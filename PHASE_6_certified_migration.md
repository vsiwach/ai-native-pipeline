# PHASE 6 — Certified migration MVP (docs-assist route)

> Claude Code session prompt. Follows the repo convention: one phase per
> session, acceptance criteria run before acceptance. Scaffolding for every
> component already exists in this branch — this phase INTEGRATES it.

## Context
You are working in ai-native-pipeline. New components (already written,
tests green): `services/docs_assist/`, `services/router/router_app/shadow.py`,
`tools/{bench,certify,replay}.py`, `tools/ragindex/`, `evals/docs_qa.jsonl`,
`deploy/runpod/`, `skills/docs-assist/`, `vercel-deploy/demo.html`.

## Your tasks, in order
1. **Registry + manifest wiring.** Run `./dev sync` so docs-assist appears in
   `inference-registry.yaml`. Fix any manifest-layer import mismatch between
   `services/docs_assist/service.py` and `tools/devkit/manifest.py` (the
   service.py has a fallback shim — replace it with the real import).
2. **Router integration.** Wire `ShadowMirror` into the router proxy path
   behind a per-route flag in `routing-policy.yaml`
   (`shadow_candidate: <url>`). Expose `GET /v1/routes/<route>/shadow-stats`,
   `POST /v1/routes/<route>/promote`, `POST /v1/routes/<route>/rollback`
   using the existing release engine (`router_app/release.py`). Promote =
   swap primary backend for the route; rollback = restore previous. Record
   both in the events log.
3. **SSE passthrough.** The router proxy must stream `text/event-stream`
   responses without buffering (contract addition: `stream: true` on
   `/v1/chat/completions`). Add a contract test.
4. **/v1/costs extension.** Add per-pool `usd_per_mtok` + `p99_ttft_ms`
   (read from `bench-reports/*.json`) and per-route `serving` + `shadowed`
   counters, matching what `vercel-deploy/demo.html` polls.
5. **./dev bench + ./dev certify.** Add devkit subcommands that shell out to
   `tools/bench.py` / `tools/certify.py`. Symlink latest cert to
   `vercel-deploy/certs/latest.json` on success.
6. **Tests + check.** `./dev check` green. Add shadow-mirror unit tests
   (mock httpx), promote/rollback release tests, and an SSE contract test.

## Acceptance criteria (run them)
- `./dev check` passes; new tests included in the count.
- `python3 tools/replay.py --loop 1` against a local docs-assist +
  llm-sim upstream produces a shadow log; `tools/certify.py run` on it
  emits a signed cert; `verify` validates; tampering invalidates.
- `demo.html?mock=true` renders full flow with no backend.
- Governance: all changes pass `tools/policy_check.py`; no production
  deploy paths added for agents.

## Non-goals
No Kubernetes, no Redis, no auth changes, no new clouds. RunPod pods are
launched manually via deploy/runpod/ — do not automate pod lifecycle in CI.
