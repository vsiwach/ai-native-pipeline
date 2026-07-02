# Overview
Source: https://docs.baseten.co/engines/engine-builder-llm/overview

Dense LLM text generation with lookahead decoding and structured outputs

Engine-Builder-LLM optimizes dense text generation models with [TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM), delivering up to 4000 tokens/second for code generation with [lookahead decoding](/engines/engine-builder-llm/lookahead-decoding). The engine supports [structured outputs](/inference/structured-outputs) for JSON schema validation.

Engine-Builder-LLM deployments mirror build artifacts to the [Baseten Delivery Network](/development/model/bdn) automatically.

## Use cases

**Model families:**

* **Llama**: `meta-llama/Llama-3.3-70B-Instruct`, `meta-llama/Llama-3.2-3B-Instruct`. For Llama 4, use [BIS-LLM](/engines/bis-llm/overview).
* **Qwen**: `Qwen/Qwen3-235B-A22B-Instruct-2507-FP8`, `Qwen/Qwen2.5-72B-Instruct`.
* **Mistral**: `mistralai/Mistral-Small-24B-Instruct-2501`, `mistralai/Mistral-7B-Instruct-v0.3`.
* **GPT-OSS**: `openai/gpt-oss-20b`.
* **Nemotron**: `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4`.
* **Gemma**: `google/gemma-3-27b-it`, `google/gemma-3-12b-it`.
* **Microsoft**: `microsoft/Phi-4`.

Engine-Builder-LLM handles high-throughput dialogue systems, coding assistants with lookahead decoding, and content generation with structured outputs. The engine's speculative decoding accelerates code generation by 2-4x, making it ideal for coding agents and JSON-heavy workloads.

### LoRA support

Engine-Builder-LLM serves multiple [LoRA adapters](/engines/engine-builder-llm/lora-support) per deployment with engine-level adapter switching. Define adapters at build time and select between them per request.

### Structured outputs

Engine-Builder-LLM supports OpenAI-compatible [structured outputs](/inference/structured-outputs) with JSON schema validation, including nested schemas and complex types.

### Key benefits

<CardGroup>
  <Card title="Low latency" icon="lightning-bolt">
    TensorRT-LLM compilation optimizes time-to-first-token.
  </Card>

  <Card title="High throughput" icon="rocket-launch">
    Batching and kernel optimization maximize tokens per second.
  </Card>

  <Card title="Lookahead decoding" icon="eye">
    Speculative decoding accelerates coding agents and predictable content.
  </Card>

  <Card title="Structured outputs" icon="shapes">
    JSON schema validation for controlled text generation.
  </Card>
</CardGroup>

## Architecture support

### Supported architectures

Engine-Builder-LLM auto-detects the Hugging Face `architectures` field from your checkpoint. The build maps each architecture to an optimized TensorRT-LLM backend:

| Hugging Face architecture                | Backend      | Example models                                 |
| ---------------------------------------- | ------------ | ---------------------------------------------- |
| `LlamaForCausalLM`, `LLaMAForCausalLM`   | LLaMA        | Llama 3.2, Llama 3.3                           |
| `MistralForCausalLM`                     | LLaMA        | Mistral 7B, Mistral Small                      |
| `AquilaForCausalLM`, `AquilaModel`       | LLaMA        | Aquila family                                  |
| `InternLMForCausalLM`                    | LLaMA        | InternLM                                       |
| `XverseForCausalLM`                      | LLaMA        | Xverse                                         |
| `Qwen2ForCausalLM`                       | Qwen         | Qwen 2.5 dense                                 |
| `Qwen2MoeForCausalLM`                    | Qwen         | Qwen 2 MoE (prefer BIS-LLM for production MoE) |
| `Qwen3ForCausalLM`                       | Qwen3        | Qwen 3 dense                                   |
| `Qwen3MoeForCausalLM`                    | Qwen3        | Qwen 3 MoE (for example, Qwen3-235B-A22B)      |
| `Palmyra4ForCausalLM`                    | Qwen         | Writer Palmyra                                 |
| `Gemma2ForCausalLM`, `Gemma3ForCausalLM` | Gemma        | Gemma 2/3 (`bf16` only)                        |
| `DeciLMForCausalLM`                      | Nemotron NAS | NVIDIA Nemotron NAS                            |

**Architectures not in this table:** If the checkpoint's `architectures` value is not listed (including `Phi3ForCausalLM` and other `ForCausalLM` variants), the build still uses `base_model: decoder` and auto-detects the architecture, logging a warning that it may miss model-specific optimizations. The legacy named `base_model` values (`llama`, `qwen`, `mistral`, `deepseek`) are no longer accepted and raise an error on push. Prefer checkpoints with explicit architecture metadata.

**Not on Engine-Builder-LLM:** Llama 4, DeepSeek MoE, Kimi, and GLM MoE use different architectures. Deploy them with [BIS-LLM](/engines/bis-llm/overview).

### Model size support

| **Model Size** | **Single GPU**         | **Tensor Parallel** | **Recommended GPU**              |
| -------------- | ---------------------- | ------------------- | -------------------------------- |
| `<8B`          | H100\_40GB, H100, B200 | N/A                 | H100\_40GB (cost-effective)      |
| 8B-30B         | H100, B200             | TP1                 | H100                             |
| 30B-70B        | H100                   | TP2-TP4             | H100 (4 GPUs)                    |
| `70B+`         | H100, B200             | TP4-TP8             | H100 (8 GPUs) or B200 (2-4 GPUs) |

## Advanced features

### Lookahead decoding

Lookahead decoding accelerates inference for code generation, JSON output, and templated content by speculating on future tokens using n-gram patterns.

**Best for:**

* **Code generation**: Highly predictable patterns in code.
* **Structured content**: Reliable JSON, YAML, XML generation.
* **Mathematical expressions**: Predictable mathematical notation.
* **Template completion**: Filling in predictable templates.

Enable lookahead decoding by adding a `speculator` section:

```yaml theme={"system"}
trt_llm:
  build:
    speculator:
      speculative_decoding_mode: LOOKAHEAD_DECODING
      lookahead_windows_size: 1
      lookahead_ngram_size: 8
      lookahead_verification_set_size: 1
      enable_b10_lookahead: true
```

**Performance impact:**

* **Speed improvement**: Up to 2x faster for code and structured content.
* **Prompt lookup**: Up to 10x faster for prompt-lookup workloads like code apply, reaching 4000 tokens/s per request on Qwen-3-8B with a single H100.
* **Optimal batch size**: Less than 32 requests for best performance.

### Structured outputs

Generate text that conforms to JSON schemas for reliable data extraction and controlled generation.

**Use cases:**

* **Data extraction**: Extract structured information from unstructured text.
* **API response generation**: Generate JSON responses for APIs.
* **Configuration generation**: Create structured configuration files.
* **Content validation**: Ensure generated content meets specific criteria.

Structured outputs work out of the box. Define a Pydantic schema:

```python theme={"system"}
import os
from pydantic import BaseModel
from openai import OpenAI

class User(BaseModel):
    name: str
    age: int
    email: str

client = OpenAI(
    api_key=os.environ['BASETEN_API_KEY'],
    base_url="https://model-xxxxxx.api.baseten.co/environments/production/sync/v1"
)

response = client.beta.chat.completions.parse(
    model="not-required",
    messages=[
        {"role": "user", "content": "Extract user info from: John is 25 years old and his email is john@example.com"}
    ],
    response_format=User
)

user = response.choices[0].message.parsed
print(f"Name: {user.name}, Age: {user.age}, Email: {user.email}")
```

### Quantization options

Engine-Builder-LLM supports multiple [quantization](/engines/performance-concepts/quantization-guide) formats. For the full GPU support matrix, model-specific recommendations, and calibration guidance, see the [quantization guide](/engines/performance-concepts/quantization-guide).

| **Quantization**                  | **Minimum GPU** | **Memory reduction** |
| --------------------------------- | --------------- | -------------------- |
| `no_quant`                        | A100            | None                 |
| `fp8`                             | L4              | \~50%                |
| `fp8_kv`                          | L4              | \~60%                |
| `fp4` / `fp4_kv` / `fp4_mlp_only` | B200            | \~75%                |

## Configuration examples

### Basic Llama 3.3 70B deployment

Llama 3.3 70B on H100 GPUs with `FP8` quantization:

```yaml theme={"system"}
model_name: Llama-3.3-70B-Instruct
resources:
  accelerator: H100:4  # 4 GPUs for 70B model
  cpu: '4'
  memory: 40Gi
  use_gpu: true
trt_llm:
  build:
    base_model: decoder
    checkpoint_repository:
      source: HF
      repo: "meta-llama/Llama-3.3-70B-Instruct"
      revision: main
      runtime_secret_name: hf_access_token
    max_seq_len: 131072
    max_batch_size: 256
    max_num_tokens: 8192
    quantization_type: fp8_kv
    tensor_parallel_count: 4
    plugin_configuration:
      paged_kv_cache: true
      use_paged_context_fmha: true
      use_fp8_context_fmha: true
    quantization_config:
      calib_size: 1024
      calib_dataset: "abisee/cnn_dailymail"
      calib_max_seq_length: 2048
  runtime:
    kv_cache_free_gpu_mem_fraction: 0.9
    enable_chunked_context: true
    batch_scheduler_policy: guaranteed_no_evict
    served_model_name: "Llama-3.3-70B-Instruct"
```

### Qwen 2.5 32B with lookahead decoding

Qwen 2.5 32B with speculative decoding for faster inference. See [Lookahead decoding](/engines/engine-builder-llm/lookahead-decoding) for the full configuration reference.

```yaml theme={"system"}
model_name: Qwen-2.5-32B-Lookahead
resources:
  accelerator: H100:1
  cpu: '2'
  memory: 20Gi
  use_gpu: true
trt_llm:
  build:
    base_model: decoder
    checkpoint_repository:
      source: HF
      repo: "Qwen/Qwen2.5-Coder-32B-Instruct"
      revision: main
    max_seq_len: 32768
    max_batch_size: 128
    max_num_tokens: 8192
    quantization_type: fp8 # no fp8_kv for qwen2.5 models
    tensor_parallel_count: 1
    num_builder_gpus: 2 # Loaded in BF16 for quantization; requires ~2x32GB (2 H100s)
    speculator:
      speculative_decoding_mode: LOOKAHEAD_DECODING
      lookahead_windows_size: 3
      lookahead_ngram_size: 8
      lookahead_verification_set_size: 3
      enable_b10_lookahead: true
    plugin_configuration:
      paged_kv_cache: true
      use_paged_context_fmha: true
      use_fp8_context_fmha: true
  runtime:
    kv_cache_free_gpu_mem_fraction: 0.85
    enable_chunked_context: true
    batch_scheduler_policy: guaranteed_no_evict
    served_model_name: "Qwen-2.5-Coder-32B-Instruct"
```

### Small model for cost-effective deployment

Llama 3.2 3B on an L4 GPU for cost efficiency:

```yaml theme={"system"}
model_name: Llama-3.2-3B-Instruct
resources:
  accelerator: L4
  cpu: '1'
  memory: 10Gi
  use_gpu: true
trt_llm:
  build:
    base_model: decoder
    checkpoint_repository:
      source: HF
      repo: "meta-llama/Llama-3.2-3B-Instruct"
      revision: main
    max_seq_len: 8192
    max_batch_size: 256
    max_num_tokens: 4096
    quantization_type: fp8
    tensor_parallel_count: 1
    plugin_configuration:
      paged_kv_cache: true
      use_paged_context_fmha: true
      use_fp8_context_fmha: false
  runtime:
    kv_cache_free_gpu_mem_fraction: 0.9
    enable_chunked_context: true
    batch_scheduler_policy: guaranteed_no_evict
    served_model_name: "Llama-3.2-3B-Instruct"
```

## Integration examples

Engine-Builder-LLM deployments are OpenAI compatible. Point `base_url` to your model's production endpoint and use the standard OpenAI SDK:

```python theme={"system"}
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ['BASETEN_API_KEY'],
    base_url="https://model-xxxxxx.api.baseten.co/environments/production/sync/v1"
)

response = client.chat.completions.create(
    model="not-required",
    messages=[{"role": "user", "content": "Explain quantum computing in simple terms."}],
    temperature=0.7,
    max_tokens=500
)

print(response.choices[0].message.content)
```

For high-throughput batch processing, use the [Performance Client](/inference/performance-client). For [structured outputs](/inference/structured-outputs) and [function calling](/inference/function-calling), see their dedicated pages.

## Sizing and tuning

Throughput, latency, and cost depend on four levers: model size, quantization (`FP8` on H100 cuts memory roughly in half, `FP4` on B200 by 75%), tensor parallelism, and whether [lookahead decoding](/engines/engine-builder-llm/lookahead-decoding) earns its keep for your workload. For the full GPU support matrix and calibration guidance, see the [quantization guide](/engines/performance-concepts/quantization-guide). For per-flag detail on `max_seq_len`, `max_batch_size`, KV cache, and chunked prefill, see the [Engine-Builder-LLM configuration reference](/engines/engine-builder-llm/engine-builder-config).

## Related

* [Configure Engine-Builder-LLM deployments](/engines/engine-builder-llm/engine-builder-config): Complete build and runtime options.
* [Set up structured outputs](/inference/structured-outputs): JSON schema validation and controlled generation.
* [Enable lookahead decoding](/engines/engine-builder-llm/lookahead-decoding): Speculative decoding for coding agents.
* [Build custom inference logic](/engines/engine-builder-llm/custom-engine-builder): Custom model.py implementation.
* [Choose a quantization format](/engines/performance-concepts/quantization-guide): FP8/FP4 trade-offs and hardware requirements.
* [Deploy LoRA adapters](/engines/engine-builder-llm/lora-support): Multi-LoRA with runtime switching.
* [Scale Engine-Builder-LLM replicas](/engines/performance-concepts/autoscaling-engines#engine-builder-llm): Autoscaling settings and concurrency targets.
