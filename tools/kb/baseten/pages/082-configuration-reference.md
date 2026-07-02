# Configuration reference
Source: https://docs.baseten.co/engines/bis-llm/bis-llm-config

Complete reference config for v2 inference stack and MoE models

This reference covers the full Truss `config.yaml` schema for BIS-LLM (Baseten Inference Stack v2). The v2 stack simplifies the `build:` section and moves runtime fields out of build.

For translating an Engine-Builder-LLM (v1) configuration to BIS-LLM, see [Migrate from Engine-Builder-LLM](/engines/bis-llm/migrate-from-v1).

## Configuration structure

```yaml theme={"system"}
trt_llm:
  inference_stack: v2  # Always v2 for BIS-LLM
  build:
    checkpoint_repository: {...}
    quantization_type: no_quant | fp8 | fp8_kv | fp4 | fp4_kv | fp4_mlp_only
    quantization_config: {...}
    num_builder_gpus: 1
    skip_build_result: false
  runtime:
    max_seq_len: 32768
    max_batch_size: 256
    max_num_tokens: 8192
    tensor_parallel_size: 1
    enable_chunked_prefill: true
    served_model_name: "model-name"
    patch_kwargs: {...}
```

## Build configuration

The `build` section configures model compilation and optimization settings.

<ParamField type="object">
  Specifies where to find the model checkpoint. Same structure as v1 with v2-specific optimizations.

  For training checkpoint deployment, see [Deploy with optimized inference engines](/training/deploy-with-engine-builder). For cloud storage sources (GCS, S3, Azure), see [Deploy from cloud storage](/engines/performance-concepts/cloud-storage-deployment).

  ```yaml theme={"system"}
  checkpoint_repository:
    source: HF | GCS | S3 | AZURE | REMOTE_URL | BASETEN_TRAINING
    repo: "model-repository-name"
    revision: main  # Optional, only for HF
    runtime_secret_name: hf_access_token  # Optional, for private repos
  ```
</ParamField>

<ParamField type="string">
  Quantization format for model weights (simplified from v1).

  **Options:**

  * `no_quant`: precision of the repo (fp16 or bf16). BIS-LLM also supports quantized checkpoints from nvidia-modelopt libraries.
  * `fp8`: FP8 weights + 16-bit KV cache
  * `fp8_kv`: FP8 weights + FP8 KV cache
  * `fp4`: FP4 weights + 16-bit KV cache (B200 only)
  * `fp4_kv`: FP4 weights + FP8 KV cache (B200 only)
  * `fp4_mlp_only`: FP4 MLP layers only + 16-bit KV cache (B200 only)

  For detailed quantization guidance including hardware requirements, calibration strategies, and model-specific recommendations, see [Quantization guide](/engines/performance-concepts/quantization-guide).

  ```yaml theme={"system"}
  build:
    quantization_type: fp8
  ```
</ParamField>

<ParamField type="object">
  Configuration for post-training quantization calibration.

  ```yaml theme={"system"}
  quantization_config:
    calib_size: 1024
    calib_dataset: "abisee/cnn_dailymail"
    calib_max_seq_length: 2048
  ```
</ParamField>

<ParamField type="number">
  Number of GPUs to use during the build process. Auto-detected from resources when unset. Minimum: 1, with no fixed maximum.

  ```yaml theme={"system"}
  build:
    num_builder_gpus: 4  # For large models or complex quantization
  ```
</ParamField>

<ParamField type="boolean">
  Skip the engine build step and use a pre-built model that does not require quantization. Use when you have a pre-built engine from model cache.

  ```yaml theme={"system"}
  build:
    skip_build_result: true
  ```
</ParamField>

## Runtime configuration

The `runtime` section configures inference engine behavior.

<ParamField type="number">
  Maximum sequence length (context) for single requests. Range: 1 to 1048576.

  ```yaml theme={"system"}
  runtime:
    max_seq_len: 131072  # 128K context
  ```
</ParamField>

<ParamField type="number">
  Maximum number of input sequences processed concurrently. Range: 1 to 2048.

  ```yaml theme={"system"}
  runtime:
    max_batch_size: 128  # Lower for better latency
  ```
</ParamField>

<ParamField type="number">
  Maximum number of batched input tokens after padding removal. Range: 65 to 131072.

  ```yaml theme={"system"}
  runtime:
    max_num_tokens: 16384  # Higher for better throughput
  ```
</ParamField>

<ParamField type="number">
  Number of GPUs to use for tensor parallelism. Auto-detected from resources. Minimum: 1, with no fixed maximum (set it to the number of GPUs in your `accelerator` setting).

  ```yaml theme={"system"}
  runtime:
    tensor_parallel_size: 4  # For large models
  ```
</ParamField>

<ParamField type="boolean">
  Enable chunked prefilling for long sequences.

  ```yaml theme={"system"}
  runtime:
    enable_chunked_prefill: true
  ```
</ParamField>

<ParamField type="string">
  Model name returned in API responses.

  ```yaml theme={"system"}
  runtime:
    served_model_name: "gpt-oss-120b"
  ```
</ParamField>

<ParamField type="object">
  Preview. Pass-through configuration patches for the v2 inference stack. Fields under `patch_kwargs` may change without notice; keys that overlap standard runtime fields are rejected at build time.

  ```yaml theme={"system"}
  runtime:
    patch_kwargs:
      custom_setting: "value"
      advanced_config:
        nested_setting: true
  ```
</ParamField>

## Complete configuration examples

### Qwen3-30B-A3B-Instruct-2507 MoE with FP4 on B200

```yaml theme={"system"}
model_name: Qwen3-30B-A3B-Instruct-2507-FP4
resources:
  accelerator: B200:1
  cpu: '4'
  memory: 40Gi
  use_gpu: true
trt_llm:
  inference_stack: v2
  build:
    checkpoint_repository:
      source: HF
      repo: "Qwen/Qwen3-Coder-30B-A3B-Instruct"
      revision: main
    quantization_type: fp4
    quantization_config:
      calib_size: 2048
      calib_dataset: "abisee/cnn_dailymail"
      calib_max_seq_length: 4096
    num_builder_gpus: 1
  runtime:
    max_seq_len: 65536
    max_batch_size: 256
    max_num_tokens: 8192
    tensor_parallel_size: 1
    enable_chunked_prefill: true
    served_model_name: "Qwen3-30B-A3B-Instruct-2507"
```

### GPT-OSS 120B on B200:1 with no\_quant

This example deploys GPT-OSS with default settings. For production throughput with Eagle speculative decoding on B200, see [Speculative decoding for BIS-LLM](/engines/bis-llm/advanced-features#speculative-decoding) and [Advanced features for BIS-LLM](/engines/bis-llm/advanced-features).

```yaml theme={"system"}
model_name: gpt-oss-120b-b200
resources:
  accelerator: B200:1
  cpu: '4'
  memory: 40Gi
  use_gpu: true
trt_llm:
  inference_stack: v2
  build:
    checkpoint_repository:
      source: HF
      repo: "openai/gpt-oss-120b"
      revision: main
      runtime_secret_name: hf_access_token
    quantization_type: no_quant
    quantization_config:
      calib_size: 1024
      calib_dataset: "abisee/cnn_dailymail"
      calib_max_seq_length: 2048
  runtime:
    max_seq_len: 131072
    max_batch_size: 256
    max_num_tokens: 16384
    tensor_parallel_size: 1
    enable_chunked_prefill: true
    served_model_name: "gpt-oss-120b"
```

### DeepSeek V3

This example deploys a pre-quantized ModelOpt checkpoint with `no_quant`. For higher throughput on DeepSeek V3 family models, use multi-GPU B200 layouts with MTP speculative decoding or disaggregated serving. See [Speculative decoding for BIS-LLM](/engines/bis-llm/advanced-features#speculative-decoding) and [Disaggregated serving](/engines/bis-llm/advanced-features#disaggregated-serving).

```yaml theme={"system"}
model_name: nvidia/DeepSeek-V3.1-NVFP4
resources:
  accelerator: B200:4
  cpu: '8'
  memory: 80Gi
  use_gpu: true
trt_llm:
  inference_stack: v2
  build:
    checkpoint_repository:
      source: HF
      repo: "nvidia/DeepSeek-V3.1-NVFP4"
      revision: main
      runtime_secret_name: hf_access_token
    quantization_type: no_quant # nvidia/DeepSeek-V3.1-NVFP4 is already modelopt compatible
    quantization_config:
      calib_size: 1024
      calib_dataset: "abisee/cnn_dailymail"
      calib_max_seq_length: 2048
  runtime:
    max_seq_len: 131072
    max_batch_size: 256
    max_num_tokens: 16384
    tensor_parallel_size: 8
    enable_chunked_prefill: true
    served_model_name: "nvidia/DeepSeek-V3.1-NVFP4"
```

## Hardware selection

**GPU recommendations for v2:**

* **B200**: Best for FP4 quantization and next-gen performance
* **H100**: Best for FP8 quantization and production workloads
* **Multi-GPU**: Required for large MoE models (>30B parameters)

**Configuration guidelines:**

| **Model Size** | **Recommended GPU** | **Quantization** | **Tensor Parallel** |
| -------------- | ------------------- | ---------------- | ------------------- |
| `<30B` MoE     | H100:2-4            | FP8              | 2-4                 |
| 30-100B MoE    | H100:4-8            | FP8              | 4-8                 |
| 100B+ MoE      | B200:4-8            | FP4              | 4-8                 |
| Dense >30B     | H100:2-4            | FP8              | 2-4                 |

## Related

* [BIS-LLM overview](/engines/bis-llm/overview): Main engine documentation.
* [Migrate from Engine-Builder-LLM](/engines/bis-llm/migrate-from-v1): Translate a v1 configuration to BIS-LLM (v2).
* [Advanced features for BIS-LLM](/engines/bis-llm/advanced-features): KV-aware routing, disaggregated serving, and speculative decoding.
* [Structured outputs for BIS-LLM](/inference/structured-outputs): JSON schema validation.
* [Model deployment examples](/examples/overview): Concrete deployment examples.
