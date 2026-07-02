# model_apis — Baseten hosted Model APIs as one catalog-driven pool

Every model in Baseten's Model API library (Kimi K2.7 Code, GLM 5.2/5.1,
Nemotron Ultra, DeepSeek V4 Pro, …) served through this repo's router, with
measured TTFT/decode and real per-token cost attribution. There is nothing to
provision: the Model APIs are serverless and multi-tenant, so **deploying
another library model is a config change** — no GPU sizing, no SKU roulette
(see docs/FRICTION_LOG.md #1–#7 for what the dedicated-SKU path cost us).

## How it fits

- **Catalog** `deploy/baseten/model-apis.json` — generated from the live
  listing: `python3 deploy/baseten/manage.py catalog --fetched-at <iso>`.
  Every alias, slug and per-1M-token price traces to that GET (provenance).
- **Manifest** [service.py](service.py) — expands the catalog into one
  registry backend per model (`./dev sync`). All entries share one image:
  the `llm_app` proxy with `ENGINE=baseten-api`.
- **Mux** `services/llm/llm_app/mux.py` — one pool process dispatches
  per-request on `model` (alias or upstream slug); unknown models fall back
  to the cheapest catalog entry so 1-token verification probes always work.
- **Adapter** `BasetenModelAPIAdapter` — Bearer auth from `BASETEN_API_KEY`
  (env only), classified upstream errors (`rate_limited | upstream_5xx |
  bad_request | unreachable`), jittered-backoff retries that never re-send
  after the stream starts, reasoning-delta-aware TTFT, per-token cost.

## Run it

```bash
# keyless: per-model sims carrying the catalog's real prices
./scripts/run_local_stack.sh

# live: same stack, real upstream
export BASETEN_API_BASE_URL=https://inference.baseten.co   # + BASETEN_API_KEY
./scripts/run_local_stack.sh

curl 'localhost:8090/v1/chat/completions' -d '{
  "model": "kimi-k2.7-code", "max_tokens": 32,
  "messages": [{"role": "user", "content": "hello"}]}'
```

Two replicas (`model-api-a/b`) serve every alias so the incident agent can
quarantine one and spill traffic to the other during chaos drills:

```bash
python3 tools/chaos.py drill --suite --model glm-4.7 --latency-ms 2600
```

## Live-pool caveats (learned the hard way — FRICTION_LOG #10, #11)

- Rate limits are **per model per workspace** with no `Retry-After`; two
  router pools on the same upstream share one quota. Keep drill load ≤0.5
  rps live; run repeatable MTTR evidence on the sim.
- `GET /v1/models` jitters >5s — it is config (snapshot it), never a
  health probe. Pool health = proxy liveness; upstream failures surface as
  classified 5xx on the request path.
