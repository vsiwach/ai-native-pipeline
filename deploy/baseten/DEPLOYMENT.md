# Live Baseten deployment — qwen3-8b-pool

Model id: `qrj78jv3` · endpoint base `https://model-qrj78jv3.api.baseten.co`

## Approach: Engine-Builder (Baseten's recommended path)
Config-only (no model.py, no Dockerfile). Baseten compiles a TensorRT-LLM
engine and serves it OpenAI-compatible. Docs: build-your-first-model +
engine-builder-config. Model Qwen3-8B (`Qwen3ForCausalLM`, supported),
single H100, fp8_kv, `tags: [openai-compatible]`.

OpenAI endpoint once ACTIVE:
`https://model-qrj78jv3.api.baseten.co/environments/production/sync/v1/chat/completions`
Auth `Authorization: Bearer $BASETEN_API_KEY`. Router BasetenAdapter points
`base_url` at `…/environments/production/sync` and uses `/v1/chat/completions`.

## Deploy history
| deployment | instance | outcome |
|---|---|---|
| wno2dv0 | L4 (2× node) | hung 30 min scheduling → INACTIVE (custom model.py, FRICTION #6) |
| w52ym5j | T4x4x16 (16GiB RAM) | OOM crash-loop on load → deactivated (custom model.py, FRICTION #7) |
| **qz47j5o** | **H100** | **Engine-Builder — BUILDING (TRT-LLM compile, active path)** |

## Cost control
- H100 ~\$6/hr active; scale-to-zero (min 0) → idle \$0; free credits cover.
- Build (fp8) may need >inference memory; if it OOMs, add `num_builder_gpus: 2`.
- `python3 deploy/baseten/manage.py deactivate qz47j5o --model-id qrj78jv3 --yes`
  when done for the day.
