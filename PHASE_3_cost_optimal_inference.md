# PHASE 3 — Cost-optimal modular inference layer

Paste everything below into Claude Code.

---

Build `services/router` — the single public entrypoint that routes inference
requests across backends and clouds for the best cost/latency trade-off.
Config-driven; zero per-model logic in code.

## Design (implement exactly this)
- FastAPI service. Reads `inference-registry.yaml` + `routing-policy.yaml` at start
  (hot-reload on SIGHUP).
- `routing-policy.yaml` (create):
  ```yaml
  tiers:
    realtime: {max_latency_ms: 250,  prefer: lowest_latency}
    standard: {max_latency_ms: 2000, prefer: lowest_cost}
    batch:    {max_latency_ms: null, prefer: lowest_cost, queue: true}
  cost_table:            # $/1M requests, maintained by ops — router just reads it
    gcp-cloudrun-cpu: 0.40
    aws-apprunner-cpu: 0.46
  cache: {enabled: true, ttl_s: 300, backend: in_memory}   # swap for redis later
  ```
- Request flow: `POST /v1/predict?model=house-price-reg&tier=standard`
  1. cache lookup (key = model + hash(payload)); return cached with `X-Cache: hit`
  2. resolve backend candidates from registry (healthy ones only — background
     health poller, 10s interval)
  3. pick endpoint per tier policy: `lowest_cost` consults cost_table;
     `lowest_latency` uses rolling p50 from the poller
  4. proxy, record latency + estimated cost, return with `X-Backend`, `X-Est-Cost`
- `tier: batch`: enqueue to a simple on-disk queue; `POST /v1/batch` returns job id,
  `GET /v1/batch/{id}` returns status/result. Worker drains queue at configured
  concurrency (this is the scale-to-zero/cheap-compute story).
- `GET /v1/costs` — running totals per backend since start (feeds the Phase 5 UI).

## Tasks
1. Implement router + tests (mock backends with stdlib http.server in tests).
2. Unit-test the policy engine hard: tier fallback, unhealthy backend skip,
   cache hit/miss, cost arithmetic.
3. Dockerfile + registry/contract updates + containers.yml picks it up automatically
   (it shouldn't need edits — that was the Phase 2 matrix design).
4. `docker-compose.yml` at root: router + inference backend, wired, for local demo.

## Acceptance criteria
- `bazel test //services/router/...` green
- `docker compose up` then: two identical predict calls — second returns `X-Cache: hit`;
  kill the backend container — router returns 503 with a clean error envelope, and
  `/healthz` on the router still returns ok (degraded=true)
- A batch job submitted, polled, and completed via /v1/batch endpoints
- `/v1/costs` shows nonzero totals after the above
