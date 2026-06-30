# CLAUDE.md — AI-Native Multi-Cloud Delivery Framework

Repo-wide instructions for Claude Code. Read fully before any task.

## What this repo is
A Bazel monorepo + CI/CD + governance framework that builds, tests, and deploys
containerized inference services to multiple clouds with cost-optimal routing.
Services are pluggable: anything implementing the inference contract
(`contracts/inference.openapi.yaml`, or the OpenAI-compatible LLM contract
`contracts/llm.openapi.yaml`) can ride the same pipeline. From Phase 6 on it is
also a **production-shaped LLM serving control plane**: a real MAX serving
backend behind the contract, a stateful KV/prefix-aware router, cold-start-aware
autoscaling + placement, reliability + safe-rollout machinery, and a DX /
observability layer — all runnable on a laptop with no GPU via a faithful
simulator, the same interfaces deploying to a real GPU when present.

## Build & test
- `bazel build //...` / `bazel test //...` — must be green before any commit
- Containers: `docker build -f services/<name>/Dockerfile .`
- Python 3.11. Services may use pip deps ONLY via their own `requirements.txt`
  consumed in Dockerfiles; Bazel targets stay stdlib-only unless a phase says otherwise.

## Architecture rules (do not violate)
1. **Contract-first**: every inference service exposes `GET /healthz`,
   `GET /v1/info` (model name, version, cost tier), `POST /v1/predict`. LLM
   backends additionally expose `POST /v1/chat/completions` (stream +
   non-stream) and `GET /v1/models` per `contracts/llm.openapi.yaml`.
2. **Modular inference**: the router (`services/router`) is the only public entry;
   model services are backends. New models = new backend + registry entry, never
   router logic changes.
3. **Cost tiers**: every backend declares `tier: realtime|standard|batch` and
   `target: cpu|gpu` in `inference-registry.yaml`. Router decisions are
   config-driven, not hard-coded.
3b. **Resources as code**: each service's container image and runtime
   resources are declared in `services/<name>/service.py` (stdlib-only
   manifest; Modal-style `Image` chaining). `inference-registry.yaml` is
   GENERATED from these by `./dev sync` — never hand-edit it; CI fails on
   drift (`./dev sync --check`).
4. **Multi-cloud neutrality**: nothing may import a cloud vendor SDK inside a
   service. All cloud specifics live in `deploy/terraform/<vendor>/`.
5. **One concern per PR.** Never mix infra and service changes.

## LLM serving platform — global design constraints (Phases 6+)
1. **Backend adapter interface.** All serving backends implement one
   `BackendAdapter` interface so the router treats them uniformly. Adapters:
   `max-local-sim` (default, no GPU), `max-container` (real `max serve`), and
   the legacy `sklearn` predict backend (kept working). Selection is
   config-driven via the manifest/registry (`engine`, `target`), never
   hard-coded in the router.
2. **No GPU required to run or test.** `max-local-sim` faithfully emulates the
   OpenAI-compatible MAX surface AND the economics that make LLM serving hard:
   per-token streaming, prefill vs decode split, a KV/prefix cache with a TTL,
   and a configurable cold-start penalty. Real GPU paths are feature-flagged
   (`target: gpu` + a GPU present) and never required for tests.
3. **Contracts first.** `contracts/llm.openapi.yaml` adds the OpenAI-compatible
   chat surface (`/v1/chat/completions` streaming + non-streaming, `/v1/models`);
   existing `/v1/predict` stays for back-compat. Contract tests gate CI.
4. **Determinism in tests.** The simulator is seedable; all timing/economics are
   injectable so unit tests are deterministic. Pure decision logic (routing,
   affinity, autoscaling, placement, failover, rollout) stays I/O-free and is
   unit-tested hard, like `router_app/policy.py`.
5. **Everything observable.** Every decision (route, scale, failover, rollout
   step) emits a structured event the devboard can render. Cost and latency
   (TTFT, tokens/sec, $/1M tokens) are first-class.

## Governance — you are subject to governance/agent-policy.yaml
- Test generation: only under `*/tests/**`, max 10 files, trailer `[agent:test-gen]`
- Staging deploys: agent-allowed when CI green. Production: humans only.
- Run `python3 tools/policy_check.py --action <action>` before pushing agent commits.

## Conventions
- Conventional commits (`feat:`, `fix:`, `infra:`, `test:`)
- Tests: unittest, in `<package>/tests/`, runnable via Bazel AND plain python
- Every new service ships with: a `service.py` manifest, Dockerfile (rendered
  from the manifest's Image), BUILD.bazel, tests, README section, and a CI job
  that exercises its /healthz in a container — `./dev new service` generates
  all of it and runs `./dev sync` for the registry entry

## Definition of done (every phase)
1. `bazel test //...` green
2. Acceptance criteria in the phase prompt demonstrably pass (show output)
3. CI workflow updated if the phase added build/deploy steps
4. README architecture table updated
