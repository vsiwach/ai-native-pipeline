# ai-native-pipeline

An **AI-native, multi-cloud delivery framework** for inference services. It takes a
model service from a single `service.py` declaration all the way to cost-routed,
multi-cloud production — with one CLI (`./dev`), one source of truth, and governance
that treats AI agents as first-class (but constrained) contributors.

> **The thesis:** model services should be *pluggable*. Anything that implements the
> inference contract rides the same pipeline — build, test, scan, publish, deploy to
> two clouds, and get cost-optimal routing — without touching framework code. Swap the
> demo house-price model for an S&P 500 model and nothing downstream changes.

Live: **https://github.com/vsiwach/ai-native-pipeline** · CI green · images on GHCR.

---

## Contents
1. [Ease of use — the 5-minute tour](#ease-of-use--the-5-minute-tour)
2. [Architecture](#architecture)
3. [Design — the decisions and why](#design--the-decisions-and-why)
4. [Future improvements — toward production scale](#future-improvements--toward-production-scale)
5. [Appendix: how this repo was built](#appendix-how-this-repo-was-built)

---

## Ease of use — the 5-minute tour

Everything is driven by one command: **`./dev`**. It's stdlib-only Python with zero
install — it works on a fresh machine *before* Bazel, Docker, or pip are set up (it's
the tool that tells you those are missing).

```bash
./dev doctor          # check your toolchain + repo health
./dev status          # where the repo stands; what to do next
```

### Ship a new model service in four commands

```bash
./dev new service sentiment --tier realtime --target gpu
#   → generates services/sentiment/{service.py, app.py, Dockerfile, BUILD.bazel,
#     tests/, README.md} + a CI job, then runs `./dev sync` to register it.

#  ... edit services/sentiment/app.py: replace predict() with your model ...

./dev test            # bazel test //...  (falls back to unittest pre-Bazel)
./dev run sentiment   # docker build + run + probe /healthz, prints the curl to try
./dev check           # the one gate before you push (see below)
```

That's the whole inner loop. The new service is **born correct**: it implements the
`/healthz`, `/v1/info`, `/v1/predict` contract, ships every artifact the conventions
require, and is registered for routing and CI — no file was hand-edited to make that
happen.

### The one command before you push

```bash
./dev check
```

runs, in order: registry validity → **manifest↔registry drift** → per-service artifact
completeness → **governance policy** → the full test suite. Green here means CI will be
green. It's the conventions in `CLAUDE.md`, *enforced* instead of remembered.

### See the whole pipeline at a glance

```bash
python3 -m http.server 8400 --directory tools/devboard
open "http://localhost:8400/?mock=true"
```

A zero-backend dashboard (React via CDN) showing CI runs, deployments per cloud, live
inference economics from the router's `/v1/costs`, and agent activity. Lighthouse
accessibility 100; `?mock=true` needs no token.

### `./dev` command reference

| Command | What it does |
|---|---|
| `./dev doctor` | Toolchain (python/bazel/docker/terraform) + repo-layout health |
| `./dev status` | Phase progress and the exact next step |
| `./dev new service <name> [--tier] [--target]` | Scaffold a contract-compliant service, manifest-first |
| `./dev sync [--check] [--dockerfiles]` | Regenerate `inference-registry.yaml` from manifests (or verify / preview) |
| `./dev test` | `bazel test //...`, unittest fallback before Bazel exists |
| `./dev build` | `bazel build //...` |
| `./dev run <name> [--port]` | Docker build + run a service, wait for `/healthz` |
| `./dev check [--action]` | Everything required before pushing |

---

## Architecture

The system is a set of **layers around one invariant** (the inference contract). Each
layer below depends only on the layers above it, and **governance + observability cut
across all of them**.

```
                         ┌───────────────────────────────────────────────┐
  Developer / Agent ───► │  ./dev  (devkit CLI, stdlib-only, zero install) │
                         └───────────────────────────────────────────────┘
                                            │  scaffold · sync · test · run · check
                                            ▼
  ① CONTRACT      contracts/inference.openapi.yaml   ← the invariant every backend honors
                  GET /healthz · GET /v1/info · POST /v1/predict
                                            │
  ② DECLARATION   services/<name>/service.py         ← resources & image AS CODE (Modal-style)
                  Image.debian_slim().pip_install()…  +  service(tier, target, scaling)
                                            │  ./dev sync   (generate, never hand-edit)
                                            ▼
  ③ SOURCE OF     inference-registry.yaml             ← generated projection of all manifests
     TRUTH        backends:{…}  services:{…}             CI fails on drift (./dev sync --check)
                                            │
            ┌───────────────────────────────┼───────────────────────────────┐
            ▼                                ▼                                ▼
  ④ BUILD/TEST            ⑤ CI/CD (GitHub Actions)            ⑦ INFRA (Terraform)
  Bazel + hermetic        containers.yml: matrix              modules/service = ONE interface
  py3.11 (bzlmod);        FROM the registry →                 ├─ gcp/  Cloud Run v2
  96 tests, runnable      build · /healthz smoke ·            └─ aws/  App Runner
  via Bazel AND           /v1/info contract check ·           envs/staging composes BOTH clouds
  plain python3           SBOM · grype · GHCR push            OIDC only — no long-lived keys
                          (main-only, policy-gated)                       │
                                            │                             │ terraform output
                                            ▼                             ▼
  ⑥ RUNTIME       services/router  ← the ONLY public entrypoint    routing-policy.yaml
                  cache → healthy candidates → tier policy          (endpoints synced back
                  (lowest_cost | lowest_latency) → proxy            in after each apply)
                  + on-disk batch queue + /v1/costs ledger
       ──────────────────────────────────────────────────────────────────────────────────
  ⓧ GOVERNANCE (cross-cutting)   governance/agent-policy.yaml + tools/policy_check.py
                                 staging✓ production✗ · publish from main only · test-gen scoped
  ⓨ OBSERVABILITY (cross-cutting) tools/devboard + router /v1/costs + MCP server (agent tools)
```

### Two control loops

- **Inner loop (the developer):** `new service → edit → test → run → check`. Fast,
  local, stdlib-friendly. Optimized for *time-to-correct-service*.
- **Outer loop (the system):** CI builds from the registry, governance gates what may
  ship and who may ship it, the router routes live traffic, the dashboard observes.
  Optimized for *verifiable correctness at rest*.

This mirrors the agent pattern itself: the inner loop does the work; the outer loop
stays independently verifiable. `./dev check` and `agent-policy.yaml` are the same idea
applied to humans and CI.

### Component map

| Layer | Component | Path | Role |
|---|---|---|---|
| ① Contract | OpenAPI specs | `contracts/inference.openapi.yaml`, `contracts/llm.openapi.yaml` | Predict + OpenAI-compatible chat surfaces |
| ⑥ LLM backend | MAX serving | `services/llm` | OpenAI-compatible chat; no-GPU MAX simulator, real `max serve` behind a flag |
| ② Declaration | Service manifests | `services/*/service.py` | Image + resources as code (stdlib-only) |
| ②→③ | devkit / `./dev` | `tools/devkit` | Scaffold, sync, test, run, check — one CLI |
| ③ | Registry | `inference-registry.yaml` | **Generated** routing/CI source of truth |
| ④ | Build system | `MODULE.bazel`, `*/BUILD.bazel` | Hermetic Python 3.11, 96 tests |
| ⑤ | Container CI | `.github/workflows/containers.yml` | Registry-driven matrix → scan → GHCR |
| ⑤ | Vuln policy | `.grype.yaml` | Fail on *actionable* criticals only |
| ⑥ | Router | `services/router` | KV/prefix affinity, cold-start-aware autoscaling, region/compliance placement, cache, batch, LLM cost metrics, event log |
| ⑥ | Placement | `placement-policy.yaml` | Regions + compliance regimes + capacity preference; compliance right-of-way on sensitive capacity |
| ⑥ | Routing policy | `routing-policy.yaml` | Tiers, cost table, cache, live endpoints |
| ⑥ | Demo backend | `services/inference` | house-price-reg (vendored, Apache-2.0) |
| ⑦ | Multi-cloud IaC | `deploy/terraform` | One interface, GCP + AWS implementations |
| ⑦ | Deploy CI | `.github/workflows/deploy-multicloud.yml` | Plan on PRs, apply via dispatch (OIDC) |
| ⓧ | Governance | `governance/agent-policy.yaml` + `tools/policy_check.py` | What agents may do |
| ⓨ | Dashboard | `tools/devboard` | Zero-backend pipeline observability |
| ⓨ | Agent tools | `tools/mcp_server.py` | `get_cloud_endpoints`, `run_terraform_plan` |

### Request lifecycle (runtime)

`POST /v1/predict?model=house-price-reg&tier=standard` hits the router and flows:

1. **Cache** — key = `model + sha256(payload)`; a hit returns immediately with
   `X-Cache: hit`.
2. **Candidates** — healthy endpoints for the model, from a background health poller
   (10s interval, rolling p50 latency per endpoint).
3. **Pick** — per the tier's policy: `lowest_cost` consults the cost table;
   `lowest_latency` uses measured p50. `batch` tier is enqueued to an on-disk queue
   instead (`/v1/batch` lifecycle) — the scale-to-zero story.
4. **Proxy** — forwards `token` auth, records latency + estimated cost, returns with
   `X-Backend` and `X-Est-Cost`.

If no backend is healthy → `503` with a clean error envelope, while the router's own
`/healthz` stays `200` with `"degraded": true`. Config (`inference-registry.yaml` +
`routing-policy.yaml`) **hot-reloads on `SIGHUP`** — no restart to reroute.

---

## Design — the decisions and why

Five decisions define this system. Each trades a little upfront machinery for a class
of bug that simply cannot occur afterward.

### 1. One generated source of truth (kills config drift)

The registry the router and CI both read is **generated** from `service.py` manifests by
`./dev sync` — never hand-edited. The Dockerfile is *rendered from the same `Image`
chain* declared in the manifest. So three things that classically drift apart — the
image definition, the Dockerfile, and the routing/scaling config — are now **one
declaration with projections**. `./dev sync --check` runs in CI and fails any PR where a
manifest changed without regenerating.

*Why this shape:* it's Modal's core ergonomic win (resources + image as code, next to
the service) **without a dependency on Modal's hosted platform** — we keep our own Bazel
+ multi-cloud stack. The manifest layer is deliberately **stdlib-only** because `./dev
sync` imports it; declaring a torch image must not require importing torch.

### 2. Contract-first, config-driven routing (kills coupling)

Every backend implements the same three-endpoint contract, and the router has **zero
per-model logic** — adding a model is a new backend + a generated registry entry, never
a router code change. Routing decisions come entirely from `routing-policy.yaml`
(tiers, cost table, endpoints). The policy *engine* (`router_app/policy.py`) is pure,
I/O-free decision logic — which is why it's the most heavily unit-tested module in the
repo (tier fallback, unhealthy-skip, cost arithmetic, latency preference).

### 3. Governance as code (makes agents safe to use)

`agent-policy.yaml` declares what an agent identity may do; `policy_check.py` (stdlib,
no deps — it must run in CI before installs) enforces it. The rules encode real
boundaries: agents may generate tests (under `*/tests/**`, ≤10 files, trailer required),
deploy to **staging only**, and **publish images from `main` only — never PR branches.**
**Production deploys are human-only and have no agent path at all.** This is what lets
the repo invite agent contributions (this very PR was agent-authored under
`[agent:test-gen]`) without surrendering the blast radius.

### 4. Cloud neutrality via one interface (kills lock-in)

`deploy/terraform/modules/service` is an *interface* — a set of variables and a `url`
output. `gcp/` (Cloud Run v2) and `aws/` (App Runner) each *implement* it. The staging
env composes the **same services onto both clouds** by swapping the module source and
nothing else. Cost guardrails are structural: both modules **refuse `max_instances > 3`**
via variable validation, and `scale_to_zero` maps to Cloud Run min-instances-0 (~$0
idle). No cloud SDK is ever imported inside a service — vendor specifics live only here.

### 5. Hermetic, dual-runnable tests (keeps the loop fast and honest)

Bazel + `rules_python` pin a hermetic Python 3.11 toolchain and a fully-locked
dependency set, so `bazel test //...` is reproducible on any machine and in CI. But
**every test also runs under plain `python3`** — so the inner loop never blocks on Bazel,
and a contributor without it can still verify. 96 tests cover the contract, the policy
engine, the cache/batch/cost subsystems, the manifest→registry generation, and the
governance rules themselves.

> **A real example of the design working:** the first CI run failed at the grype gate on
> base-image CVEs that *no rebuild can fix* (Debian "won't-fix", CPython-fixed-only-in-a-beta).
> The fix wasn't to weaken the gate — it was `.grype.yaml` scoping it to **actionable**
> findings (a fix exists → still fails the build) while documenting the unfixable ones,
> with the full SBOM still attached as the audit trail.

---

## Future improvements — toward production scale

What exists is a coherent, end-to-end *framework*. To run it as a **production-scale dev
productivity pipeline** serving many teams and models, here's the roadmap, by theme and
rough priority.

### Runtime & scale
- **Distributed cache + queue.** The TTL cache and batch queue are in-process /
  on-disk by design (the interfaces anticipate this). Swap to Redis for the cache and a
  real broker (SQS / Pub/Sub / Celery) for batch so the router can run N replicas.
- **Real autoscaling signals.** Routing uses rolling p50; add p95/p99, error-rate, and
  queue-depth as routing and scaling inputs. Lift the structural `max_instances ≤ 3`
  guardrail into a per-tier budget policy.
- **GPU backends end-to-end.** `target: gpu` is modeled but the demo is CPU. Wire GPU
  node pools (Cloud Run GPU / App Runner alternatives like GKE/EKS) through the same
  module interface.
- **Streaming & async contract.** Add `POST /v1/predict:stream` (SSE) to the contract
  for token-streaming models; the router proxy and devboard already centralize the seams.

### Reliability & operability
- **Observability stack.** Emit OpenTelemetry traces/metrics from the router; ship
  `/v1/costs` to Prometheus + Grafana so the devboard reads real history, not a polled
  snapshot. Add structured logs with request IDs across the proxy hop.
- **Progressive delivery.** Canary / blue-green at the routing layer — weight traffic
  by version in `routing-policy.yaml`, auto-rollback on error-budget burn.
- **Remote Terraform state + drift detection.** Migrate from local state (path is
  documented) to GCS/S3 with locking; add scheduled `terraform plan` to detect infra
  drift the way `./dev sync --check` detects config drift.
- **DR & multi-region.** The two-cloud composition is the seed of real failover —
  add health-based cross-cloud routing and per-region endpoints.

### Supply chain & security
- **Sign and attest.** Cosign image signatures + SLSA provenance; verify signatures at
  deploy admission. The SBOM is already produced — gate on it.
- **Secrets management.** Move `INFERENCE_API_KEY` and GHCR creds to Secret Manager /
  Secrets Manager with rotation; mTLS or signed JWTs between router and backends instead
  of a shared header key.
- **Continuous, scheduled scanning.** Run grype on a schedule (not just on change) so
  newly-disclosed CVEs in unchanged images surface; auto-open remediation PRs.

### Developer productivity (the core promise, at fleet scale)
- **`./dev` as a versioned, distributable tool.** Package it (pipx / a pinned release)
  so many repos share one devkit; today it's vendored in-tree.
- **Remote build cache + CI sharding.** A shared Bazel remote cache and test sharding so
  CI time stays flat as services multiply; only rebuild/retest what the diff touches
  (Bazel already knows the graph).
- **Golden-path templates beyond the default.** `./dev new service --template
  {pytorch-gpu, sklearn-cpu, llm-vllm}` — more starting points, same contract.
- **Preview environments per PR.** Spin an ephemeral staging stack per pull request
  (the dispatch-gated deploy is most of the way there) and tear it down on merge/close.
- **Self-service docs site.** Generate API reference from the OpenAPI contract and a
  service catalog from the registry, published on merge.

### Governance & AI-native workflow
- **Richer policy engine.** Move `agent-policy.yaml` toward OPA/Rego or Cedar for
  expressive rules (rate limits, cost ceilings per agent, time-of-day windows) while
  keeping the stdlib fast-path for CI.
- **Cryptographic agent attribution.** Today agent authorship is a commit trailer;
  sign agent commits and verify the identity claimed by the policy check.
- **Cost & quality budgets as gates.** Make `/v1/costs` trends a release gate (block a
  deploy that would blow a tier's cost budget); track agent-PR human-edit rate as a
  quality signal (the devboard already surfaces it).
- **Expand the MCP surface.** The server exposes read-only plan + endpoint tools today;
  add governed, auditable write paths (open-PR, request-staging-deploy) so agents drive
  the outer loop within policy.

---

## Appendix: how this repo was built

This framework was built with Claude Code, **one phase per session**, each phase ending
in acceptance criteria run before acceptance — the same outer-loop/inner-loop discipline
the framework itself embodies. The phase prompts are preserved in the repo root.

| Phase | Builds | Path |
|---|---|---|
| `PHASE_1_…` | Vendor a real model service behind the contract | `services/inference` |
| `PHASE_2_…` | Container CI: registry matrix, scan, GHCR, deploy gates | `.github/workflows`, governance |
| `PHASE_3_…` | Cost-optimal router: tiers, cache, batch, scale-to-zero | `services/router` |
| `PHASE_4_…` | Multi-cloud Terraform: GCP Cloud Run + AWS App Runner | `deploy/terraform` |
| `PHASE_5_…` | Developer dashboard over the whole pipeline | `tools/devboard` |

The framework is app-agnostic: the demo house-price model is just the first thing behind
the contract. A future `PHASE_6` that swaps in an S&P 500 model is a new backend and
nothing else — which is the proof the architecture is modular.

## Repository conventions

See **[CLAUDE.md](CLAUDE.md)** for the binding rules (contract-first, generated registry,
one-concern-per-PR, governance). In short: declare services in `service.py`, never
hand-edit the registry, run `./dev check` before pushing, and let the contract — not
framework edits — absorb new models.
