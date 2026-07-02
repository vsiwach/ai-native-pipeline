# STAFF-SKEPTIC — model-apis

**Verdict: FAIL** (top objection is neither fixed nor documented as a known
limit; everything else about this feature is genuinely strong).

Reviewed: working-tree diff on `baseten-mvp` (BasetenModelAPIAdapter +
ModelAPIMux, catalog pipeline, chat failover, incident-agent fixes, MTTR
drill runner, docs). Live sim stack verified at `http://localhost:8096`.
Note: no SLO-AUDITOR or CHAOS-AGENT reports existed in `evals/model-apis/`
at review time — this review had to reconstruct their evidence from
`benchmarks/raw/` directly.

## JD lines: claimed vs actually demonstrated

Actually demonstrated:
- *Health-aware recovery from stuck or bad replicas* — detect → quarantine →
  probe → reinstate → resolve loop, with the same-tick quarantine race and
  last-pool guard fixed and unit-tested (`services/router/tests/
  test_incident_agent.py`), and honest failed-drill rows retained in
  `benchmarks/raw/chaos_drills.csv`.
- *Self-serve incident management with measured MTTR* — `tools/chaos.py
  drill --suite` produces a timeline CSV per drill; the hero MTTR (8.1s)
  traces `/v1/metrics/hero` → `/v1/incidents` → the 16:31–16:33 rows of
  `chaos_drills.csv`. Provenance chain holds.
- *Cost/perf frontier instrumentation* — measured (not modeled) TTFT/decode,
  per-token cost attribution whose prices trace to a catalog snapshot
  generated from the live `/v1/models` GET (`deploy/baseten/manage.py
  catalog`), reasoning-delta-aware TTFT latching (FRICTION_LOG #11 — real
  learned behavior).
- *Workload onboarding as config* — catalog → `SERVICES` expansion →
  generated registry (`tools/devkit/sync.py`), registry stays generated per
  CLAUDE.md rule 3b. Verified: no vendor SDK imports (stdlib urllib only).

Claimed but NOT demonstrated:
- *"Every request reaches a healthy replica"* — see objection 1: with every
  replica returning 5xx, clients receive HTTP 200. Failover triggers on
  transport errors only.
- *"Measurable decline in MTTR"* — `mttr_delta_pct` is 0.0; there is no
  manual-baseline MTTR anywhere in `benchmarks/raw/` to decline from.
- *Redundancy via two replicas* — both replicas share one upstream key and
  one per-model quota (FRICTION_LOG #10). This one IS documented
  (services/model_apis/README.md caveats) — credited as a known limit.

## Ranked objections

### 1. TOP — router converts backend errors into HTTP 200s; 429s are invisible to breach accounting (UNRESOLVED → FAIL)

- `services/router/router_app/main.py:545` — non-stream chat returns
  `JSONResponse(content=resp.json(), headers=headers)`: the pool's status
  code is discarded, default 200.
- `services/router/router_app/main.py:~268-282` (proxy_chat_stream) — the
  stream path never inspects `upstream.status_code`; a pool 429/502/500 at
  connect is re-emitted as `200 text/event-stream` whose body is a raw,
  non-SSE-framed JSON error with no `[DONE]`.
- **Empirically demonstrated on the live stack (2026-07-02):** injected
  `error_rate=1.0` on BOTH mux replicas via their `/chaos` hooks; the router
  answered `router_status=200` for streaming AND non-streaming
  `/v1/chat/completions`, body `{"error":{"type":"chaos_injected_5xx"}}`.
- Compounding: `main.py:245` and `main.py:329` set
  `http_ok = status_code < 500`, so a **429 storm — the exact live failure
  mode this feature's own FRICTION_LOG #10 documents (25/40 requests
  rate-limited)** — is recorded as SLO-met traffic. No breach, no incident,
  no escalation, clients get 200s. The pool-level fix in this very diff
  (`llm_app/main.py` `_upstream_error_response`, "never a 200") is undone
  one hop later.
- This contradicts the feature README's claim that "upstream failures
  surface as classified 5xx on the request path" and is documented nowhere
  as a limit. It is the 3am pager: goodput collapses, board and clients
  both read green/200.
- **Fix is small:** propagate `resp.status_code` on the non-stream return;
  check `upstream.status_code` before committing the StreamingResponse
  (fail over or return the real status — the stream is uncommitted at that
  point, exactly the window the pool-level fix exploited); count 429 as
  not-ok (or as a distinct `rate_limited` goodput signal that can open an
  incident of kind the agent escalates rather than quarantine-spills).

### 2. Blocking calls on the asyncio event loop — the 100x collapse point

- `services/llm/llm_app/main.py:107-111`: `next(lines)` inside
  `async def chat_completions` blocks the pool's event loop for the full
  TTFT (real upstream network time on live; `sse_stream`'s `time.sleep`
  pacing on the sim mux path, since `ModelAPIMux` always has `stream_raw`).
- `services/llm/llm_app/main.py:122`: non-stream `backend.generate(req)`
  blocks the loop for the entire completion.
- `services/router/router_app/main.py` proxy_chat_stream: sync
  `httpx.stream(...).__enter__()` in async context (the non-stream path
  uses `run_in_threadpool` — the authors knew; the stream path doesn't).
- The async chaos-gate fix comment in this diff states the rule verbatim
  ("must never block the event loop and take the whole pool (including
  /healthz) down with it") and the code below it violates it. At ~3 rps
  with 2.6s injected latency the drills already show the symptom: failed
  rows with 162–254 client errors (`chaos_drills.csv` 15:35, 15:41, 16:13).
  At 50 rps: loop saturation → /healthz starvation → poller flap →
  failover storm. Additionally each in-flight stream holds an anyio
  threadpool worker (default ~40/process) — a hard concurrency ceiling.

### 3. Chat failover is transport-only; /v1/predict's is status-aware

`main.py:362-365` (predict) marks unhealthy and retries the next replica on
`resp.status_code >= 500`; the new chat loops retry only on
`httpx.HTTPError`. A replica answering 502 goes straight to the client (as
a 200, per objection 1) even with a healthy replica available. The
docstring claims parity ("failover, like /v1/predict always had") —
oversold.

### 4. Two-replica spill shares one upstream quota — DOCUMENTED, accepted

model-api-a/b are two local proxies over the same key and per-model
quota; quarantine-and-spill relocates load onto the same limit, and probes
compete with spilled traffic. Honestly written up (FRICTION_LOG #10 +
README caveats, drill guidance ≤0.5 rps live, sim for repeatable MTTR).
The devboard autoscaler card (`replicas 1/2`) still *renders* a redundancy
story the physics don't back — worth a caveat in the pool card or README.

### 5. Mux silently serves the wrong model on unknown `model`

`mux.py:51-56`: unknown → default alias, HTTP 200, default's prices. Tested
as intended (`test_unknown_model_falls_back_to_default`) and README'd, but
an OpenAI-compatible surface should return `model_not_found`. The router's
`UnknownModel` guard covers the front door; alias drift between the two
separately-refreshed generated artifacts (registry via `./dev sync`,
catalog via `manage.py catalog`) or direct pool access silently swaps
models and mis-attributes cost.

### 6. routing-policy.yaml endpoints are hand-pasted, O(models)

11 identical two-replica blocks (~70 lines). The registry is generated;
the policy endpoints are not. At 200 models that's ~1,200 hand-maintained
lines and the "new model = config, never code" story quietly acquires a
copy-paste drift risk. Generate this block from the catalog too.

### 7. Minor

- `mux.py:152-154`: default alias = `min(usd_per_1m_completion, default
  0.0)` — a catalog entry with a missing price becomes the default.
- `tools/chaos.py` drill matches incidents by `pool in i["title"]`
  substring — brittle against pool-id prefixes.
- Incident agent + devboard watch a single `DEVBOARD_MODEL`; fine at 2
  pools, structurally single-model at 200.
- `OpenAICompatAdapter.healthz` cache mutates `refreshing` without a lock
  (benign double-refresh race).

## Allowlist check — PASS

Executor ops verified in `incident_agent.py`: open/act (bookkeeping),
quarantine, probe, reinstate, resolve, and `escalate` which **only emits an
`agent_escalation` event** (no paging side effect, no scale/deploy/config
mutation). Escalation fires exactly once, probes slow-poll 5x afterward,
quarantine held. Tight.

## Devboard contract check — PASS

- Six endpoints unchanged and live on :8096 (`/v1/metrics/hero`,
  `/v1/metrics/slo`, `/v1/pools`, `/v1/placement/feed`, `/v1/releases/
  active`, `/v1/incidents`).
- SLO thresholds from API, not hard-code: standard tier ttft 2000 / tpot 80
  rendered in `/v1/metrics/slo` traces to `routing-policy.yaml:8`.
- Traced number: hero `mttr_s: 8.1` → `/v1/incidents` INC-0001..3 →
  `benchmarks/raw/chaos_drills.csv` rows 20260702-1631/1632/1633.
- `cost_per_mtok` is computed from measured samples
  (`metrics.py:98-101`), not the cost_table ranking value. No fabricated
  values found. Caveat: hero `mttr_delta_pct` renders 0.0 because no manual
  baseline exists — a gap in the "decline vs manual" story, not a
  fabrication.

## 100x analysis (11 models × 2 replicas → 200 models, 50 rps)

- **Models axis mostly scales:** catalog → generated registry is O(1) human
  effort; but routing-policy endpoints (objection 6) and the
  single-DEVBOARD_MODEL watch (objection 7) do not.
- **Throughput axis does not:** blocking event loops (objection 2) +
  ~40-worker threadpool ceiling per proxy process cap each pool far below
  50 rps of multi-second streams; the failure mode is healthz starvation →
  poller flap → failover storm, already visible in the failed drill rows.
- **Quota axis is honest but coupled:** replicas multiply proxy capacity,
  not upstream quota; incident-agent spill can worsen a 429 brownout it
  cannot even see (objection 1).

## Resolution required for PASS

Fix objection 1 (propagate real status on both chat paths + make 429 a
non-ok/goodput-loss signal), or at minimum add it to the
services/model_apis/README.md caveats as a known limit with the client
impact stated plainly. Re-run one `drill --scenario errors` to show a 5xx
storm reaching clients as 5xx.
