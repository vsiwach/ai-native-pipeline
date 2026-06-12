# CLAUDE.md — AI-Native Multi-Cloud Delivery Framework

Repo-wide instructions for Claude Code. Read fully before any task.

## What this repo is
A Bazel monorepo + CI/CD + governance framework that builds, tests, and deploys
containerized inference services to multiple clouds with cost-optimal routing.
Services are pluggable: anything implementing the inference contract
(`contracts/inference.openapi.yaml`) can ride the same pipeline.

## Build & test
- `bazel build //...` / `bazel test //...` — must be green before any commit
- Containers: `docker build -f services/<name>/Dockerfile .`
- Python 3.11. Services may use pip deps ONLY via their own `requirements.txt`
  consumed in Dockerfiles; Bazel targets stay stdlib-only unless a phase says otherwise.

## Architecture rules (do not violate)
1. **Contract-first**: every inference service exposes `GET /healthz`,
   `GET /v1/info` (model name, version, cost tier), `POST /v1/predict`.
2. **Modular inference**: the router (`services/router`) is the only public entry;
   model services are backends. New models = new backend + registry entry, never
   router logic changes.
3. **Cost tiers**: every backend declares `tier: realtime|standard|batch` and
   `target: cpu|gpu` in `inference-registry.yaml`. Router decisions are
   config-driven, not hard-coded.
4. **Multi-cloud neutrality**: nothing may import a cloud vendor SDK inside a
   service. All cloud specifics live in `deploy/terraform/<vendor>/`.
5. **One concern per PR.** Never mix infra and service changes.

## Governance — you are subject to governance/agent-policy.yaml
- Test generation: only under `*/tests/**`, max 10 files, trailer `[agent:test-gen]`
- Staging deploys: agent-allowed when CI green. Production: humans only.
- Run `python3 tools/policy_check.py --action <action>` before pushing agent commits.

## Conventions
- Conventional commits (`feat:`, `fix:`, `infra:`, `test:`)
- Tests: unittest, in `<package>/tests/`, runnable via Bazel AND plain python
- Every new service ships with: Dockerfile, BUILD.bazel, tests, registry entry,
  README section, and a CI job that exercises its /healthz in a container

## Definition of done (every phase)
1. `bazel test //...` green
2. Acceptance criteria in the phase prompt demonstrably pass (show output)
3. CI workflow updated if the phase added build/deploy steps
4. README architecture table updated
