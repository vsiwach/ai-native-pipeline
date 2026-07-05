# Phase 6 — certified migration: decisions log

Autonomous session on branch `phase-6-certified-migration` (2026-07-05).
Each entry: what was decided, why, and what a human may want to revisit.

## Integration (task A)
- **Input zips** were not at the `~/Downloads` paths named in the run
  instructions; the user supplied session-output paths under
  `~/Library/Application Support/Claude/...` and those were used.
- `deploy/runpod/README.md` was **overwritten** by the drop's version (the
  old pod.py-era README is in git history at `2c53803`). `pod.py` and
  `spend-ledger.json` were left untouched.
- Pre-existing dirty files `.claude/launch.json` (modified) and `tools/mcp/`
  (untracked) predate this session and were **excluded** from Phase 6 commits.
- Both zips carry `vercel-deploy/demo.html` + `certs/latest.json`;
  `endpoint-game-app.zip` (newer, 15:45) won since the instructions say it
  replaces `vercel-deploy/` wholesale.

## B1 — registry + manifest wiring
- `services/docs_assist/service.py` rewritten against the real
  `tools/devkit/manifest.py` API (module-level `SERVICE = service(...)` +
  `Image` chain), replacing the drop's decorator-style shim. Deviations from
  the shim's kwargs:
  - `engine="openai-proxy"` kept — added `"openai-proxy"` to
    `VALID_ENGINES` (additive; the registry entry now names the adapter
    kind, and the devboard's engine-based model pick ignores it, which is
    correct — docs-assist is a route, not the watched LLM pool).
  - `route="docs-assist"` dropped: route name == service name by
    convention; the router keys routes on the registry/model name.
  - `egress_class="in-vpc"` dropped from the manifest (no such field in the
    Service schema and no consumer); the in-VPC intent is documented in
    service.py + README instead. Revisit if placement ever enforces egress.
- Dockerfile regenerated from the manifest Image chain (repo-root build
  context, `/srv` workdir, non-root user, healthcheck — repo conventions;
  the drop's Dockerfile assumed a service-local context, which `./dev run`
  does not use).
- Added missing required artifacts: `BUILD.bazel` (tests-only, like other
  services), `tests/bazel_runner.py`, `tests/__init__.py`, `README.md`,
  and `kb/README.md` (the sqlite index is a built artifact, not committed).
