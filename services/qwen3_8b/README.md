# qwen3-8b — one model, two pools (baseten-mvp)

The mission's serving entry: `qwen3-8b` is a single registry backend with two
replica endpoints in `routing-policy.yaml` — the Baseten pool (Truss,
`engine=baseten`) and the RunPod vLLM pool (`engine=vllm`). Both replicas run
the `llm_app` proxy from `services/llm` (this directory holds only the
manifest + rendered Dockerfile; there is no code fork).

| | sim (default) | live |
|---|---|---|
| Baseten pool | no `BASETEN_BASE_URL` → local sim, pool-tuned economics | `BASETEN_BASE_URL` + `BASETEN_API_KEY` → `BasetenAdapter` (measured TTFT/decode/$) |
| vLLM pool | no `VLLM_BASE_URL` → local sim | `VLLM_BASE_URL` (+ optional `VLLM_API_KEY`) → `VllmAdapter` |

Adapters: `services/llm/llm_app/openai_compat.py` (stdlib streaming, injectable
I/O, tests in `services/llm/tests/test_openai_compat.py`). Live adapters
measure wall-clock TTFT/decode by always streaming upstream and attribute cost
as the request's wall-clock share of the pool's `POOL_USD_PER_HOUR`.

Run both pools + router locally: `docker compose up --build` (sim, $0). Flip
live by exporting the URLs/keys — no rebuild, per rule 3b/manifest env.
