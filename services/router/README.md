# router — the single public inference entrypoint

Routes `POST /v1/predict?model=<name>&tier=<tier>` across backends and clouds
for the best cost/latency trade-off. Entirely config-driven: decisions come
from `inference-registry.yaml` (what exists) and `routing-policy.yaml` (how to
choose) — zero per-model logic in code. Both hot-reload on `SIGHUP`.

## Request flow — `/v1/predict` (stateless, Phase 3)

1. **Cache** — key = model + sha256(payload); hits return `X-Cache: hit`.
2. **Candidates** — healthy endpoints for the model (background poller, 10s).
3. **Pick** — per tier policy: `lowest_cost` consults the cost table,
   `lowest_latency` uses rolling p50 from the poller.
4. **Proxy** — forwards the `token` auth header; failed endpoints are marked
   unhealthy and the next candidate is tried; responses carry `X-Backend`
   and `X-Est-Cost`.

## Request flow — `/v1/chat/completions` (stateful, Phase 7)

LLM serving is stateful: a request sharing a prompt prefix is far cheaper on
the replica that already holds that prefix's KV (a hit skips prefill). So the
router selects a **replica**, not just a provider, via a layered decision
([`policy.select_replica`](router_app/policy.py), pure / I/O-free):

1. **placement filter** — region / compliance eligibility (Phase 8 hook).
2. **prefix affinity** — a warm replica already holding the prefix wins;
   otherwise a [consistent-hash ring](router_app/affinity.py) gives the prefix
   a stable home, so identical prefixes keep landing together and a failed
   replica's traffic re-lands consistently (not a global reshuffle).
3. **least-pending** — skip replicas at capacity; prefer fewer in-flight.
4. **tier preference** — `lowest_cost` / `lowest_latency` as the final tiebreak.

`/v1/costs` reports LLM-native metrics per backend — **TTFT, tokens/sec,
cache-hit rate, $/1M tokens**. `/v1/events` streams every route decision (and,
from Phases 8–9, scale / failover / rollout) for the devboard.

```bash
# affinity ON vs OFF over a bounded-KV fleet (deterministic):
python3 services/router/scripts/affinity_bench.py
#   affinity OFF   hit 0.28   ttft 354ms
#   affinity ON    hit 0.98   ttft 100ms
```

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
