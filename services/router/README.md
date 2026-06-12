# router — the single public inference entrypoint

Routes `POST /v1/predict?model=<name>&tier=<tier>` across backends and clouds
for the best cost/latency trade-off. Entirely config-driven: decisions come
from `inference-registry.yaml` (what exists) and `routing-policy.yaml` (how to
choose) — zero per-model logic in code. Both hot-reload on `SIGHUP`.

## Request flow

1. **Cache** — key = model + sha256(payload); hits return `X-Cache: hit`.
2. **Candidates** — healthy endpoints for the model (background poller, 10s).
3. **Pick** — per tier policy: `lowest_cost` consults the cost table,
   `lowest_latency` uses rolling p50 from the poller.
4. **Proxy** — forwards the `token` auth header; failed endpoints are marked
   unhealthy and the next candidate is tried; responses carry `X-Backend`
   and `X-Est-Cost`.

Batch tier requests are enqueued instead (on-disk queue, survives restarts):
`POST /v1/batch?model=…` → job id; `GET /v1/batch/{id}` → status/result.
`GET /v1/costs` exposes per-backend totals for the Phase 5 dashboard.

No healthy backend → `503` with `{"error": {"code": "no_healthy_backend", …}}`;
the router's own `/healthz` stays `200` with `"degraded": true`.

## Run the full stack locally

```bash
docker compose up --build
curl -X POST 'localhost:8090/v1/predict?model=house-price-reg' \
  -H 'token: local-dev-key' -H 'Content-Type: application/json' \
  -d @services/inference/docs/sample_payload.json
```

## Test

```bash
bazel test //services/router/...
# mock backends are stdlib http.server — see tests/conftest.py
```

## Files

- `router_app/policy.py` — the pure policy engine (tier resolve + selection)
- `router_app/health.py` — poller, rolling p50, unhealthy marking
- `router_app/cache.py` — in-memory TTL cache (redis is a drop-in later)
- `router_app/batch.py` — on-disk queue + worker pool
- `router_app/costs.py` — running cost ledger for /v1/costs
- `service.py` — resources & image as code (renders the Dockerfile)
