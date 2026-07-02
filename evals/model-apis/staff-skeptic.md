# STAFF-SKEPTIC — model-apis

**Verdict: PASS** (re-review 2026-07-02, after commit f647380 addressed the
top objection; prior verdict was FAIL for status laundering).

Reviewed: commit f647380 on `baseten-mvp` (BasetenModelAPIAdapter +
ModelAPIMux, catalog pipeline, chat failover, incident-agent fixes, MTTR
drill runner, docs) plus the fixes for my two lead objections folded into
that commit. Live sim stack re-verified at `http://localhost:8096`
(pools :8103/:8104, DEVBOARD_MODEL=glm-4.7). SLO-AUDITOR report present
(`evals/model-apis/slo-auditor.md`); evidence files in
`evals/model-apis/evidence/`.

## Re-verification of the prior FAIL (top objection)

### Objection 1 — status laundering + invisible 429s: FIXED, verified 3 ways

Code (`services/router/router_app/main.py`):
- `:595` non-stream return is `JSONResponse(..., status_code=resp.status_code)`
  with the comment naming this finding; `:556-558` stream return is
  `StreamingResponse(..., status_code=up_status)`.
- `:260-267` non-stream: backend 5xx → replica added to `tried`, next replica
  selected via `_select_for_chat(exclude=tried)` (`:145-148` — exclusion
  beats prefix affinity, so failover can't re-pick the sick pool); if every
  replica 5xx's, the LAST REAL 5xx is returned ("be honest").
- `:303-317` stream: `upstream.status_code >= 500` is caught BEFORE the
  stream commits; breach recorded against the sick pool
  (`http_ok=False`), failover event emitted, next replica tried.
- `:258-259` and `:369-370`: `http_ok = status < 500 and status != 429` —
  a 429 now feeds breach detection (the FRICTION_LOG #10 failure mode is
  no longer invisible). 429 does NOT trigger failover — correct, since both
  replicas share one upstream quota (retrying would amplify the storm).

Tests (`services/router/tests/test_chat_failover.py`, 5/5 pass):
transport failover both modes, backend-5xx failover with breach recorded
against the sick pool, and `test_all_replicas_5xx_returns_real_status_not_200`
— the exact scenario I demonstrated. Full suites: router 110 pass,
llm 54 pass.

Live re-demonstration (2026-07-02, this review):
1. `POST /chaos {"error_rate":1.0}` on BOTH pools → router
   `/v1/chat/completions` returned **500** non-stream (body
   `{"error":{"type":"chaos_injected_5xx"}}`) and **503**
   `no_healthy_backend` streaming. Previously both were 200.
2. Healed pool-b only → both modes returned **200** served by
   `X-Replica: model-api-b`; `failover` events (`upstream 500`) and
   `slo_breach` samples recorded against BOTH pools from step 1;
   incident agent ejected model-api-a (still sick) and — bonus —
   INC-0003 shows the last-pool guard live ("last healthy pool,
   quarantine withheld" on model-api-b).
3. Cleared chaos → agent probed and reinstated; both pools `steady`,
   INC-0002/0003 resolved with measured MTTR. Stack left clean.
4. 429 accounting verified empirically with a one-off harness (mock
   backend answering 429): client received **429**, and a `slo_breach`
   was recorded against the pool. Not laundered, not invisible.

### Objection 2 — event-loop blocking: FIXED (loop safety); ceiling remains

- `services/llm/llm_app/main.py:112` first-line pull and `:128`
  `backend.generate` now run via `run_in_threadpool`; the chaos gate's
  latency sleep is `asyncio.sleep`.
- `services/router/router_app/main.py:545,559` — both chat modes call the
  blocking proxy (including the stream connect) through
  `run_in_threadpool`. Sync body generators are iterated by Starlette's
  own threadpool, so /healthz can no longer be starved by a slow pool.
- **Follow-up (not blocking, should be a known limit):** each in-flight
  stream still pins an anyio threadpool worker (default ~40/process) —
  a hard per-process concurrency ceiling at 100x. The loop-starvation
  pager is gone; the ceiling is a capacity fact, not a correctness bug.

### Objection 3 — chat failover transport-only: FIXED

Both chat modes now retry on backend 5xx with the `tried` exclusion set,
matching (and in stream mode exceeding) the `/v1/predict` guarantee. The
docstring's parity claim is now earned.

## Objections still open (follow-ups, none blocking)

4. Two-replica spill shares one upstream key/quota — DOCUMENTED
   (FRICTION_LOG #10 + `services/model_apis/README.md` caveats), accepted.
   The devboard autoscaler card still renders a redundancy story the quota
   physics don't back.
5. Mux serves the default alias on unknown `model` with the default's
   prices (`services/llm/llm_app/mux.py:51-56`); router front door guards
   it, direct pool access doesn't. Tested-as-intended and README'd, but an
   OpenAI-compatible surface should 404 `model_not_found`.
6. `routing-policy.yaml` endpoint blocks are hand-pasted per model
   (~70 lines for 11 models); registry is generated, this isn't. At 200
   models the "config, never code" story acquires copy-paste drift.
7. Minor: default alias picks `min(price, default 0.0)` so a missing price
   wins (`mux.py:152-154`); `tools/chaos.py` matches incidents by title
   substring; single `DEVBOARD_MODEL` watch; `healthz` cache refresh race
   (benign). NEW minor: no committed router test for 429
   propagation/breach (verified here via one-off harness — add one so a
   regression can't silently reintroduce it); stream all-replicas-5xx
   returns 503 `no_healthy_backend` rather than the last backend's real
   5xx body (non-stream returns the real one) — honest but inconsistent.

## JD lines actually demonstrated (unchanged + upgraded)

- *Health-aware recovery from stuck/bad replicas* — now includes
  status-aware chat failover; detect → quarantine → last-pool guard →
  probe → reinstate → resolve observed LIVE during this re-review.
- *"Every request reaches a healthy replica"* — NOW demonstrated: with one
  sick and one healthy pool, clients got 200 from the healthy replica;
  with zero healthy pools, clients got honest 5xx.
- *Self-serve incident management with measured MTTR* — provenance chain
  (hero → /v1/incidents → chaos_drills.csv) holds; still no manual
  baseline, so `mttr_delta_pct` 0.0 ("measurable decline" remains
  unproven — follow-up, not a fabrication).
- *Cost/perf frontier instrumentation* and *workload onboarding as
  config* — as before (catalog → generated registry, measured economics,
  no vendor SDK imports).

## Allowlist check — PASS (unchanged)

Incident-agent executor ops: open/act, quarantine, probe, reinstate,
resolve, escalate (event-only, fires once, slow-poll after). Tight.

## Devboard contract check — PASS (unchanged)

Six endpoints live; SLO thresholds from `/v1/metrics/slo` trace to
`routing-policy.yaml`, not hard-code; hero `mttr_s` traces to
`benchmarks/raw/chaos_drills.csv`; `cost_per_mtok` computed from measured
samples. No fabricated values. Caveat: `mttr_delta_pct` renders 0.0 (no
manual baseline).

## 100x analysis (revised)

- **Throughput axis, revised:** loop starvation → healthz flap → failover
  storm is fixed (threadpool offload both hops). The new ceiling is the
  ~40-worker anyio pool per process pinned by long streams — degradation
  is now queuing (slow, visible in TTFT/breach metrics) instead of
  control-plane collapse (healthz lying). Strictly better failure mode;
  size the pool or go native-async before 50 rps of multi-second streams.
- **Models axis:** catalog → generated registry scales; hand-pasted
  routing-policy endpoints (obj. 6) and single-model devboard watch
  (obj. 7) don't.
- **Quota axis:** honest and now VISIBLE — 429s reach clients as 429 and
  feed breach accounting, so a quota brownout opens an incident instead
  of rendering green. Spill still can't manufacture upstream quota
  (documented).

## Resolution of the prior top objection

Fix verified (code + 5 passing tests + live chaos re-demonstration + 429
harness). Prior FAIL is lifted. Remaining follow-ups (threadpool ceiling,
429 router test, mux unknown-model default, policy-endpoint generation,
MTTR baseline) do not block.
