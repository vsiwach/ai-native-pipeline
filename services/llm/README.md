# llm — OpenAI-compatible LLM serving (MAX)

An LLM backend behind the contract in [`contracts/llm.openapi.yaml`](../../contracts/llm.openapi.yaml).
One `BackendAdapter` interface, three implementations selected by the manifest —
**no GPU required to run or test.**

| Adapter | `engine` / `target` | When |
|---|---|---|
| `MaxLocalSim` | `max` / `cpu` | **Default.** Faithful no-GPU simulator |
| `MaxContainer` | `max` / `gpu` | Proxies a real `max serve` (needs a GPU) |
| `SklearnPredict` | `sklearn` / `cpu` | Wraps the legacy `/v1/predict` backend |

## What the simulator models (and why)

`MaxLocalSim` emulates the *economics* that make LLM serving hard, so routing,
caching, and autoscaling decisions are visibly economic without a GPU:

- **prefill vs decode split** — TTFT ∝ prompt tokens (prefill), throughput ∝
  output tokens (decode).
- **KV/prefix cache with a TTL** — a prompt sharing a cached prefix skips most of
  prefill (cost drops to ~10%); entries expire after `kv_ttl_s`.
- **cold-start penalty** — a cold replica pays `cold_start_s` before first token.

Everything is **seedable and clock-injected**, so unit tests are deterministic
(see `llm_app/economics.py`).

## Run (no GPU)

```bash
./dev run llm --port 8100              # build + run + a sample streaming chat
./dev chat "what is prefill vs decode?" --port 8100 --stream
# or the whole stack:
docker compose up --build
```

You'll see the cold replica pay ~8s TTFT on the first call, then a second
identical prompt return in <1ms with `X-Cache: hit` — the prefix cache + warm
replica at work.

## Endpoints

`GET /healthz` · `GET /v1/info` (advertises `engine`, `target`, `capabilities`)
· `GET /v1/models` · `POST /v1/chat/completions` (stream + non-stream). Responses
carry economics headers: `X-Cache`, `X-TTFT-Ms`, `X-Tokens-Per-Sec`,
`X-Est-Cost`, `X-Prompt-Tokens`, `X-Completion-Tokens`.

## Switching to a real MAX engine (when you have a GPU)

The framework is cloud-agnostic and deploy-later: the *same* adapter interface
swaps to a real engine with **zero router or app code changes** — only the
manifest + env change.

```bash
# Option A — run MAX directly on a GPU box:
uv pip install --pre --upgrade modular
max serve --model google/gemma-3-12b-it --devices gpu:0 --max-batch-size 8

# Option B — the official container:
docker run --gpus=1 -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  modular/max-nvidia-full:latest --model google/gemma-3-12b-it
```

Then in `service.py` set `target="gpu"` and run the service with
`MAX_BASE_URL=http://localhost:8000` (and `MODEL_ID` to the served model). The
factory selects `MaxContainer`, which proxies `max serve`'s OpenAI-compatible
endpoint. `./dev sync` regenerates the registry; the router uses it unchanged.

## Test

```bash
bazel test //services/llm/...
# economics determinism, KV cache + TTL, cold start, adapter conformance,
# and the OpenAI contract (stream + non-stream).
```
