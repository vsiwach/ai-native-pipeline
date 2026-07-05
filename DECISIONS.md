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

## B2 — shadow wiring
- The drop's `shadow.py` scheduled mirrors with
  `asyncio.get_event_loop().create_task(...)`, which raises in the chat
  proxy's threadpool threads (no running loop). Adapted: a module-owned
  background loop thread (lazy) + `run_coroutine_threadsafe`, and a
  `flush()` helper; counters land only after the JSONL line is on disk so
  `flush()` implies evidence exists.
- Mirroring hooks the **non-streaming** chat path only (what
  `tools/replay.py` sends). Streaming primaries are not mirrored: the
  primary's content isn't buffered on the streaming path, and the mirror
  compares full completions by design (it strips `stream`). Revisit only if
  the replayer goes streaming.
- Promote/rollback are **in-memory** traffic shifts (same semantics as the
  existing `POST /v1/policy/placement`): a SIGHUP policy reload restores the
  file's endpoints. Deliberate — the file stays the durable source of truth
  and a human edit is the durable promote.
- Promote uses `Release(mode=canary, steps=(100,))` — start → advance →
  COMPLETE with warmup+drain recorded — because the phase defines promote as
  a full swap, not a staged canary. The shadow phase itself is evidenced by
  the mirror's stats/log rather than a `Release(mode=shadow)` object (the
  release engine's shadow mode models traffic weights, not evidence capture).
- Governance: nothing agent-facing calls promote; `prod-shift` stays
  human-only in `agent-policy.yaml`. The endpoints are dev/staging controls
  on a local router.

## B3 — SSE
- The streaming path was ALREADY unbuffered (verified 12ms first-token
  passthrough while the backend was mid-generation) — Phase 6's task was
  satisfied by pinning it with a contract test. Starlette's TestClient
  buffers streamed responses, so the timing assertion runs at the
  generator level; the HTTP-layer test covers media type + headers.

## C — KB index (LIVE, not fixture)
- Network was available; built from the real sitemaps
  (docs.modular.com + modular.com/blog): **2690 chunks, index sha256
  ac3a4da77cc0093f51aaa34f04e3e367da7a959242991700f50cc4548f200843**
  (2026-07-05, `--max-pages 400`). The sqlite artifact is gitignored;
  rebuild with `tools/ragindex/build_index.py` (the sha will drift as docs
  change — certs embed the eval-set sha, and the verification report embeds
  the index sha).

## D — eval fact verification
- Added `tools/ragindex/verify_evals.py`: every `must_include` keyword is
  classified RETRIEVED (in top-k for its question) / IN_CORPUS / MISSING;
  report committed at `evals/docs_qa.verification.json` (embeds index sha).
- **q02 rewritten.** The seed asserted the Mojo compiler open-sources
  "fall 2026" — that string exists NOWHERE in the crawled corpus (Mojo docs
  moved to mojolang.org, outside the indexer's allow-list), so the agent
  could never ground it. Replaced with the corpus-supported fact (stdlib
  core modules open source + nightly compiler builds, per the "Next Big
  Step in Mojo Open Source" post). The old claim was a drop-provided seed
  the MVP_README itself said to re-verify. If mojolang.org is added to the
  crawler allow-list later, a dated-timeline question can return.
- q11 has only `must_not_include` guards (by design) — flagged NO_KEYWORDS,
  nothing to verify positively.
- Result after fix: 12/12 items clean, 0 MISSING.

## E — end-to-end loop (sim)
- `scripts/run_migration_loop.sh` runs the whole thing:
  llm-sim → docs-assist(primary)+docs-assist(candidate) → router with
  shadow route → replay → certify → verify → tamper → promote/rollback
  drill. Evidence committed at `demo-artifacts/20260705T202234Z/`.
- **Two certs, deliberately.** At the real gate (0.90) the sim run is
  verdict **HOLD** with parity 0.0% — the lorem-token sim can't emit `[n]`
  citation markers, so grounding honestly fails; that cert is in
  `certs-gate90/`. A second run with `--gate-parity 0.0` (gate value is
  printed inside the signed record — nothing hidden) produces the
  PROMOTE_ELIGIBLE cert that exercises the ./dev certify symlink path.
  Meaningful parity numbers require a real instruction-following model on
  a GPU pod — listed as needs-a-human in SUMMARY.md.
- Two loop-runner bugs found live and fixed: `./dev bench --flag` lost its
  leading flags to the parent argparse (REMAINDER quirk → early dispatch),
  and backgrounded subshells leaked their python children on cleanup
  (`exec env ...` so the recorded pid IS the server; plus a port preflight
  and a hard shadow-log existence check).
- `vercel-deploy/certs/latest.json` is now a relative symlink into
  `demo-artifacts/` (committed). A real Vercel deploy must copy the cert
  instead (symlink escapes the deploy root) — noted in SUMMARY.md.
- First-attempt run dirs from the two failed script iterations were
  deleted; only the passing run's artifacts are committed.

## Post-phase, user-driven (2026-07-05, same session)
- **CORS**: env-gated `ROUTER_CORS_ORIGINS` (off by default) so the static
  console origin can poll the router from the browser.
- **Grounding headers**: X-Citations/X-Retrieval-Ms now forwarded on both
  chat paths (found live: the console chip lost its sources).
- **demo.html robustness**: unknown serving ids degrade to em-dashes
  instead of killing the poll loop; `.actions` wraps on narrow viewports.
- **Synthetic load**: user decided the demo should self-drive rather than
  rely on agent Q&A (the sim's lorem answers are by design — economics,
  not language). Two shapes: `tools/loadgen.py` (CLI, CSV evidence) and
  `/v1/dev/loadgen` + a console button (in-router runner, bounded ≤20 rps
  ≤600 s, one run at a time, start/done events). Requests traverse the
  ordinary chat path so shadow/metrics/ledger see real traffic. A stopped
  run may count its aborted in-flight request as 1 error — honest artifact
  of hard-stop.

## Public live console (user-driven, 07-05 late)
- The whole demo stack (llm-sim + docs-assist ×2 + router) runs as ONE
  Modal web app (`deploy/modal/router_stack.py`) so the Vercel console can
  be DRIVEN by an external reviewer with no laptop involved. The router is
  the only exposed port (repo architecture rule survives the hosting hop).
- `max_containers=1`: the router is stateful (shadow log, loadgen run,
  ledger, releases); Modal auto-scaling split state across two containers
  in testing — a GET landed on a different replica than the POST that
  started the run. Singleton or bust.
- `LOADGEN_TARGET=http://127.0.0.1:8114`: the in-container loadgen cannot
  hairpin through its own public *.modal.run URL (100% connection errors);
  self-load targets localhost. Loadgen status now carries `last_error`.
- Mutating surfaces (loadgen/gpu/chaos POSTs, promote/rollback) gate on
  ROUTER_DEV_TOKEN when set (Modal Secret; console passes ?token=...).
  RunPod key lives in the same Secret; browser never sees either.
- Modal MAX endpoint registered as a first-class pool (`GPU_MODAL_URL` →
  `modal-a100` entry: adopt/bench/certify; no launch/terminate — the
  platform scales to zero on idle, and terminate answers with that note).
- Replay narration: `tools/replay_captions.py` derives captions from the
  recorded trace (pod rented/ready, load start/finish, cert verdict,
  promote/rollback, teardown) — shown in a REPLAY NARRATION card;
  captions are generated from events, never authored fiction.

## F — quality gates
- `./dev check` surfaced two PRE-EXISTING artifact gaps (not Phase 6's):
  `services/model_apis` and `services/qwen3_8b` had no BUILD.bazel or
  tests/. Both are declaration-only pool services (the app is
  services/llm's llm_app), so the honest testable surface is the manifest
  itself: contract fields, catalog expansion (model_apis), and
  Dockerfile == exact manifest render (drift guard — both held). Added
  minimal suites + BUILD targets + a `deploy/baseten` filegroup for the
  catalog. `./dev check` now fully green (13 bazel test targets).
- CI (`containers.yml`) needed NO change: the build matrix is generated
  from the registry, so docs-assist joined automatically; its image builds
  (kb/README.md satisfies the COPY) and /healthz answers 200.
- `.claude/launch.json` stays uncommitted: it carried the user's own
  pre-session edit; my only addition is the local `demo-site` static
  server entry used to verify `demo.html?mock=true`.
- `tools/mcp/` (untracked, pre-session) left untouched.
