# Overview
Source: https://docs.baseten.co/engines/bis-llm/overview

Token-based autoscaling, KV-aware routing, disaggregated serving, and speculative decoding for MoE and large dense models

BIS-LLM (Baseten Inference Stack v2) is the engine for Mixture of Experts (MoE) models and large dense LLMs. It targets MoE families (DeepSeek V3.x, Qwen3MoE, Kimi-K2, Llama 4, GLM-4.7, GPT-OSS 120B) and the largest dense models, where the standard request-based autoscaler and a single-server inference engine both leave performance on the table. The v2 stack adds token-based autoscaling, KV-aware routing, disaggregated serving, expert parallel load balancing, and DP attention. Deployments mirror build artifacts to the [Baseten Delivery Network](/development/model/bdn) so cold starts stay fast.

<BisLlmEnterpriseGate />

## Production features

BIS-LLM ships four features that the standard inference path doesn't include. Token-based autoscaling lives on the [Autoscaling engines](/engines/performance-concepts/autoscaling-engines#bis-llm) page; the other three are documented together in [Advanced features for BIS-LLM](/engines/bis-llm/advanced-features).

<CardGroup>
  <Card title="Token-based autoscaling" href="/engines/performance-concepts/autoscaling-engines#bis-llm" icon="chart-line">
    Scales replicas on `target_in_flight_tokens` rather than request concurrency, so mixed-length prompt workloads scale on real compute load.
  </Card>

  <Card title="KV-aware routing" href="/engines/bis-llm/advanced-features#kv-aware-routing" icon="route">
    Routes requests to the worker most likely to serve them from KV cache. Lower time-to-first-token on prefix-overlapping traffic.
  </Card>

  <Card title="Disaggregated serving" href="/engines/bis-llm/advanced-features#disaggregated-serving" icon="layer-group">
    Splits prefill and decode onto independent worker groups that scale separately.
  </Card>

  <Card title="Speculative decoding" href="/engines/bis-llm/advanced-features#speculative-decoding" icon="bolt">
    Eagle, MTP, and N-gram speculation. Multiple tokens per forward pass on supported architectures.
  </Card>
</CardGroup>

## A canonical configuration

The `trt_llm` block in `config.yaml` configures the build and runtime. A pre-quantized DeepSeek V3 deployment on B200 looks like:

```yaml config.yaml theme={"system"}
model_name: deepseek-v3-1-nvfp4
resources:
  accelerator: B200:4
  use_gpu: true
trt_llm:
  inference_stack: v2
  build:
    checkpoint_repository:
      source: HF
      repo: "nvidia/DeepSeek-V3.1-NVFP4"
      runtime_secret_name: hf_access_token
    quantization_type: no_quant  # ModelOpt-quantized checkpoint
  runtime:
    max_seq_len: 131072
    max_batch_size: 256
    tensor_parallel_size: 4
    enable_chunked_prefill: true
    served_model_name: "deepseek-v3"
```

After `truss push`, the build compiles the engine, the BDN mirrors weights to GPU-local storage, and the deployment exposes OpenAI-compatible `/v1/chat/completions`. The four production features above each plug in through their own configuration blocks; see [BIS-LLM configuration](/engines/bis-llm/bis-llm-config) for the complete reference and additional examples (GPT-OSS 120B, Qwen3-MoE, Llama 3.3 70B).

For tuning advice on a specific or fine-tuned model, [contact your Baseten representative](mailto:support@baseten.co).

## OpenAI-compatible inference

BIS-LLM deployments expose `/v1/chat/completions`, `/v1/completions`, and `/v1/embeddings` (where applicable). Standard OpenAI client SDKs work without modification:

```python theme={"system"}
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ["BASETEN_API_KEY"],
    base_url="https://model-xxxxxx.api.baseten.co/environments/production/sync/v1"
)

response = client.chat.completions.create(
    model="not-required",
    messages=[{"role": "user", "content": "Explain mixture of experts in two sentences."}],
)
```

[Structured outputs](/inference/structured-outputs) and [function calling](/inference/function-calling) are supported through the standard OpenAI parameters and have their own reference pages.

## Observability

BIS-LLM emits metrics from three components. Each has its own dashboard section:

| Domain               | Metric prefix              | Page                                                                                |
| -------------------- | -------------------------- | ----------------------------------------------------------------------------------- |
| Autoscaler decisions | `autoscaler_*`             | [Autoscaling engines](/engines/performance-concepts/autoscaling-engines#monitoring) |
| Router and KV cache  | `kv_cache_*`               | [KV-aware routing](/engines/bis-llm/advanced-features#kv-aware-routing)             |
| Engine and request   | engine-level metrics below | This page                                                                           |

Engine-level metrics, available on every BIS-LLM deployment:

| Metric                                                          | What it measures                                                                                                      |
| --------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `tps_per_request`                                               | Tokens per second per request.                                                                                        |
| `input_tokens` / `output_tokens`                                | Total token throughput across the deployment.                                                                         |
| `input_tokens_per_request` / `output_tokens_per_request`        | Per-request token averages.                                                                                           |
| `concurrent_requests`                                           | Currently in-flight request count.                                                                                    |
| `speculation_rate`                                              | Draft-token acceptance rate when speculative decoding is active. High rates indicate the draft model is well-aligned. |
| `cpu_usage` / `memory_usage` / `gpu_usage` / `gpu_memory_usage` | Resource utilization per replica.                                                                                     |
| `replica_count_by_status`                                       | Replica counts grouped by lifecycle status.                                                                           |

Start with `tps_per_request` to confirm replicas handle load as expected. If you run Enterprise features, add `kv_cache_hit_rate` (KV-aware routing, in the router domain) or `speculation_rate` (Eagle/MTP) next. See [Advanced features for BIS-LLM](/engines/bis-llm/advanced-features#speculative-decoding) for speculative-decoding configuration that produces `speculation_rate`.

## Migrate from Engine-Builder-LLM

Engine-Builder-LLM is the v1 stack. Migrating to BIS-LLM is mostly moving runtime fields out of `build:`, renaming `tensor_parallel_count` to `tensor_parallel_size`, and removing fields v2 handles automatically (`plugin_configuration`, `base_model`). Autoscaling, speculation, and routing also change in ways that aren't just renames. See [Migrate from Engine-Builder-LLM](/engines/bis-llm/migrate-from-v1) for the field-by-field mapping, the semantic changes, and the validation errors you might see during cutover.

## Related

* [BIS-LLM configuration reference](/engines/bis-llm/bis-llm-config): Complete v2 configuration options.
* [Migrate from Engine-Builder-LLM](/engines/bis-llm/migrate-from-v1): Translate a v1 configuration to BIS-LLM.
* [Advanced features for BIS-LLM](/engines/bis-llm/advanced-features): KV-aware routing, disaggregated serving, and speculative decoding.
* [Autoscaling engines](/engines/performance-concepts/autoscaling-engines#bis-llm): Configure target in-flight tokens for BIS-LLM deployments.
* [Structured outputs](/inference/structured-outputs): JSON schema validation.
* [Examples section](/examples/overview): Concrete deployment examples.
