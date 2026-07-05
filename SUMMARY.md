# Phase 6 — certified migration: summary

Branch `phase-6-certified-migration`, 2026-07-05, autonomous session.
Decision trail: [DECISIONS.md](DECISIONS.md). One commit per phase task.

## What was built

**Integration (A).** The certified-migration MVP drop (docs-assist service,
shadow mirror, bench/certify/replay tools, ragindex, evals, RunPod scripts,
docs-assist skill) merged into the repo, and the unified Vercel site
(hub + brief + strategy + prd + mvp + demo) replaced `vercel-deploy/`.

**Registry + manifest (1).** `services/docs_assist/service.py` rewritten
against the real devkit manifest layer (`SERVICE` + `Image` chain,
`engine: openai-proxy` added to the schema); Dockerfile regenerated for the
repo-root build context; BUILD.bazel/README/tests added; `./dev sync` emits
the docs-assist registry entry; CI's registry-driven matrix picks it up with
zero workflow edits.

**Shadow mirror (2).** `ShadowMirror` wired behind
`routing-policy.yaml routes: {<route>: {shadow_candidate: <url>}}`. While
the primary serves the client, the candidate receives a mirror of every
non-streaming chat request; `(request, primary, candidate, timings,
citations)` append to `shadow-logs/<route>.shadow.jsonl`. Mirrors run on a
dedicated background loop (fire-and-forget, capped in-flight, failures
recorded never surfaced). `GET /v1/routes/<r>/shadow-stats`,
`POST …/promote` (endpoint swap through the release engine, events
recorded), `POST …/rollback` (restores saved endpoints, 409 when there is
nothing to roll back). Compose now runs incumbent + candidate docs-assist
instances against the llm sim.

**SSE (3).** The streaming path was already unbuffered; it is now pinned by
a contract test — first token leaves the router while the backend is still
generating (~12 ms passthrough), media type + economics headers survive.

**/v1/costs (4).** Additive `pools` (latest `tools/bench.py` report per
pool: measured `usd_per_mtok`, `p99_ttft_ms`, declared $/hr — repeated,
never estimated) and `routes` (`serving` replica + `shadowed` count) —
exactly what `vercel-deploy/demo.html` polls.

**./dev bench + ./dev certify (5).** Passthrough subcommands; a
PROMOTE_ELIGIBLE certify run relinks `vercel-deploy/certs/latest.json`
(relative symlink) to the newest cert.

**KB index (C).** Built LIVE from the public docs sitemaps: 2690 chunks,
sha256 `ac3a4da7…`. The sqlite artifact is gitignored and reproducible;
`tools/ragindex/build_index.py --offline-dir` remains the no-network path.

**Eval verification (D).** New `tools/ragindex/verify_evals.py` classifies
every `must_include` keyword RETRIEVED / IN_CORPUS / MISSING against the
built index (report: `evals/docs_qa.verification.json`). Seed q02 claimed
the Mojo compiler open-sources "fall 2026" — a fact absent from the
crawlable corpus (Mojo docs moved to mojolang.org) — rewritten to the
corpus-supported open-source facts. 12/12 clean.

**End-to-end loop (E).** `scripts/run_migration_loop.sh` on the sim stack,
evidence in `demo-artifacts/20260705T202234Z/`:
replay 12/12 → shadow 12/12 mirrored (0 failed) → bench (374 tok/s
aggregate, p99 TTFT 121 ms) → certify **HOLD at the real 0.90 gate**
(the lorem sim cannot emit citations — honest zero parity; cert in
`certs-gate90/`) and PROMOTE_ELIGIBLE at a declared gate of 0 for the
plumbing cert → `verify` VALID → tampered copy INVALID → promote served
`x-replica: docs-assist-candidate` → rollback restored `frontier`.
`demo.html?mock=true` verified rendering backendless (labeled MOCK MODE;
promote/rollback flow works client-side).

**Quality (F).** `./dev check` fully green: registry valid (15 backends),
zero manifest drift, all six services artifact-complete, governance
ALLOWED, 13 bazel test targets pass. New tests this phase: 4 shadow-mirror
(mocked httpx), 6 release-route, 2 SSE contract, 2 costs-surface, 4
cert-link, plus manifest suites for the two pool services `./dev check`
flagged as pre-existing gaps (model_apis, qwen3_8b — declaration-only, so
the tests pin contract fields + Dockerfile == exact manifest render).
`tools/policy_check.py` ALLOWED for push/test-gen; `compileall` clean.
No agent-reachable production deploy path was added; promote/rollback are
dev/staging router controls and `prod-shift` stays human-only.

## What needs a human

1. **RunPod pod launch** — `deploy/runpod/launch_pod.sh` + `serve_max.sh`
   (MAX-first, vLLM fallback). Costs real money (~$1.2–1.9/hr A100,
   MI300X per console); the repo's $40 budget guard and the "user decides
   spend" rule both apply. RunPod provisioning was also flaky on 07-02
   (friction #16) — verify pods actually boot.
2. **Real GPU bench + certification numbers** — rerun
   `./dev bench` against the pod, then the certify gate at 0.90 with a real
   instruction-following model; the sim's parity is honestly 0 and the
   HOLD cert proves the gate bites. Only then do demo.html's live numbers
   mean anything.
3. **Vercel deploy** of `vercel-deploy/` — also decide how `certs/latest.json`
   ships: it is a symlink into `demo-artifacts/` which will NOT resolve on
   Vercel's static deploy; copy the cert file in a deploy step (one-liner)
   or vendor it before `vercel --prod`.
4. **Skills-repo PR** — `skills/docs-assist/SKILL.md` is packaged for
   Modular's skills-repo conventions; opening the PR is outward-facing and
   human-gated.
5. **Optional**: grow `evals/docs_qa.jsonl` from 12 seeds toward ~150 using
   `tools/ragindex/suggest_evals.py` + human curation; add mojolang.org to
   the indexer allow-list if Mojo-compiler-timeline facts should certify.

## Honest caveats

- Parity numbers from the sim are meaningless by construction (no
  citations); every committed cert says which gate it was issued under.
- Promote/rollback are in-memory traffic shifts (like
  `POST /v1/policy/placement`); a SIGHUP reload restores
  `routing-policy.yaml` — the file remains the durable source of truth.
- Streaming requests are served token-by-token but not shadow-mirrored
  (the mirror compares full completions); the replayer sends non-streaming.
- The KB index sha drifts as Modular's docs change; certs bind the eval-set
  sha and the verification report binds the index sha.
