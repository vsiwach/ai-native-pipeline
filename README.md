# Claude Code Prompt Pack — AI-Native Multi-Cloud Delivery Framework

Build a complete framework — coding → CI/CD → cost-optimal inference → multi-cloud
deployment → dev-facing UX — using Claude Code, one phase per session.

## How to use

1. Start from the `ai-native-pipeline` repo (Bazel monorepo + CI + governance + MCP
   server you already have). Copy `CLAUDE.md` from this pack into the repo root
   (replaces the existing one — it's a superset).
2. Open Claude Code in the repo. Paste **one phase prompt per session**, in order.
   Each phase ends with acceptance criteria — make Claude run them before you accept.
3. Commit after every green phase. The framework is app-agnostic: the dummy
   inference app (Phase 1) can later be swapped for your S&P 500 financial app —
   it's just another service behind the same contract.

## Phases

| File | Builds | Session size |
|---|---|---|
| `PHASE_1_vendor_inference_app.md` | Vendor eightBEC/fastapi-ml-skeleton as `services/inference` | small |
| `PHASE_2_cicd_containers.md` | Container builds, GHCR push, deploy gates in Actions | medium |
| `PHASE_3_cost_optimal_inference.md` | Modular inference: router, tiers, cache, scale-to-zero | large |
| `PHASE_4_multicloud_deploy.md` | Terraform: GCP Cloud Run + AWS App Runner + failover | large |
| `PHASE_5_devtool_ux.md` | Dev dashboard (React, Claude-style design) over the pipeline | medium |

## Architecture

| Component | Path | Role |
|---|---|---|
| Inference contract | `contracts/inference.openapi.yaml` | The surface every backend implements (`/healthz`, `/v1/info`, `/v1/predict`) |
| house-price-reg | `services/inference` | First backend — vendored from eightBEC/fastapi-ml-skeleton (Apache-2.0), standard tier, cpu |
| Backend registry | `inference-registry.yaml` | Config-driven routing source of truth (tier, target, scaling) |
| devkit | `tools/devkit` | `./dev` productivity CLI |

## Dev productivity: `./dev`

The repo ships a single-command developer framework ([tools/devkit](tools/devkit/README.md),
stdlib-only Python, zero install):

```bash
./dev status                 # phase progress + exact next step
./dev doctor                 # toolchain & repo health
./dev new service <name>     # scaffold a contract-compliant service (all artifacts)
./dev test                   # bazel test //... (unittest fallback pre-Bazel)
./dev run <name>             # docker build+run + /healthz probe
./dev check                  # everything required before pushing
```

`new service` generates app.py (the full `/healthz` `/v1/info` `/v1/predict`
contract), tests, Dockerfile, BUILD.bazel, README, a container-healthz CI job,
and the `inference-registry.yaml` entry — the conventions in CLAUDE.md,
enforced by `./dev check` instead of remembered.

## Why phases instead of one mega-prompt

Each phase fits in one Claude Code context window with room to run builds and tests.
Acceptance criteria per phase = the "outer loop" stays verifiable while the agent
does the inner loop. (This is the same governance idea as `agent-policy.yaml`.)

## Later: the financial app

When ready, a `PHASE_6` prompt simply replaces the dummy model with an S&P 500
model service implementing the same `/v1/predict` contract — zero framework change.
That's the proof the architecture is modular.
