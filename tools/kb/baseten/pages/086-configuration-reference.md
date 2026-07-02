# Configuration reference
Source: https://docs.baseten.co/engines/engine-builder-llm/engine-builder-config

Complete reference config for dense text generation models

This reference covers all build and runtime options for Engine-Builder-LLM deployments. All settings use the `trt_llm` section in `config.yaml`.

## Configuration structure

```yaml theme={"system"}
trt_llm:
  inference_stack: v1  # Always v1 for Engine-Builder-LLM
  build:
    base_model: decoder
    checkpoint_repository: {...}
    max_seq_len: 131072
    max_batch_size: 256
    max_num_tokens: 8192
    quantization_type: no_quant | fp8 | fp8_kv | fp4 | fp4_kv | fp4_mlp_only
    quantization_config: {...}
    tensor_parallel_count: 1
    plugin_configuration: {...}
    speculator: {...}  # Optional for lookahead decoding
  runtime:
    kv_cache_free_gpu_mem_fraction: 0.9
    enable_chunked_context: true
    batch_scheduler_policy: guaranteed_no_evict
    served_model_name: "model-name"
    total_token_limit: 500000
```

## Build configuration

Fields are tagged **Required**, **Optional**, or **Computed**. Computed fields are set by the engine; do not configure them manually.

The `build` section configures model compilation and optimization settings.

<ParamField type="string">
  **Required.** The base model architecture for your model checkpoint.

  **Options:**

  * `decoder`: For CausalLM models (Llama, Mistral, Qwen, Gemma, Phi)

  ```yaml theme={"system"}
  build:
    base_model: decoder
  ```
</ParamField>

<ParamField type="object">
  **Required.** Specifies where to find the model checkpoint. Repository must be a valid Hugging Face model repository with the standard structure (config.json, tokenizer files, model weights).

  **Source options:**

  * `HF`: Hugging Face Hub (default)
  * `GCS`: Google Cloud Storage
  * `S3`: AWS S3
  * `AZURE`: Azure Blob Storage
  * `REMOTE_URL`: HTTP URL to tar.gz file
  * `BASETEN_TRAINING`: Baseten Training checkpoints

  For training checkpoint deployment, see [Deploy with optimized inference engines](/training/deploy-with-engine-builder). For cloud storage sources (GCS, S3, Azure), see [Deploy from cloud storage](/engines/performance-concepts/cloud-storage-deployment).

  ```yaml theme={"system"}
  checkpoint_repository:
    source: HF
    repo: "meta-llama/Llama-3.3-70B-Instruct"
    revision: main
    runtime_secret_name: hf_access_token
  ```
</ParamField>

<ParamField type="number">
  **Optional.** Maximum sequence length (context) for single requests. Range: 1 to 1048576.

  ```yaml theme={"system"}
  build:
    max_seq_len: 131072  # 128K context
  ```
</ParamField>

<ParamField type="number">
  **Optional.** Maximum number of input sequences processed concurrently. Range: 1 to 2048.

  Keep this at 256. It only affects performance when lookahead decoding is enabled.
  Recommended not to be set below 8 to keep performance dynamic for various problems.

  ```yaml theme={"system"}
  build:
    max_batch_size: 256
  ```
</ParamField>

<ParamField type="number">
  **Optional.** Maximum number of batched input tokens after padding removal in each batch. Range: 65 to 1048576 (`gt=64, le=1048576` in schema).

  If `enable_chunked_prefill: false`, this also limits the `max_seq_len` that can be processed. Recommended: `8192` or `16384`.

  ```yaml theme={"system"}
  build:
    max_num_tokens: 16384
  ```
</ParamField>

<ParamField type="string">
  **Optional.** Specifies the quantization format for model weights.

  **Options:**

  * `no_quant`: `FP16`/`BF16` precision
  * `fp8`: `FP8` weights + 16-bit KV cache
  * `fp8_kv`: `FP8` weights + `FP8` KV cache
  * `fp4`: `FP4` weights + 16-bit KV cache (B200 only)
  * `fp4_kv`: `FP4` weights + `FP8` KV cache (B200 only)
  * `fp4_mlp_only`: `FP4` MLP only + 16-bit KV (B200 only)

  For detailed quantization guidance, see [Quantization Guide](/engines/performance-concepts/quantization-guide).

  ```yaml theme={"system"}
  build:
    quantization_type: fp8_kv
  ```
</ParamField>

<ParamField type="object">
  **Optional.** Configuration for post-training quantization calibration.

  **Fields:**

  * `calib_size`: Size of calibration dataset (64-16384, multiple of 64). Defines how many rows of the train split with text column to take.
  * `calib_dataset`: HuggingFace dataset for calibration. Dataset must have 'text' column (str type) for samples, or 'train' split as subsection.
  * `calib_max_seq_length`: Maximum sequence length for calibration (default: 2048).

  ```yaml theme={"system"}
  build:
    quantization_type: fp8
    quantization_config:
      calib_size: 1536
      calib_dataset: "abisee/cnn_dailymail"
      calib_max_seq_length: 1536
  ```
</ParamField>

<ParamField type="number">
  **Optional.** Number of GPUs to use for tensor parallelism. Minimum: 1, with no fixed maximum. Must equal the number of GPUs in your `accelerator` resource setting.

  ```yaml theme={"system"}
  build:
    tensor_parallel_count: 4  # For 70B+ models
  ```
</ParamField>

<ParamField type="object">
  **Optional.** TensorRT-LLM plugin configuration for performance optimization.

  **Fields:**

  * `paged_kv_cache`: Enable paged KV cache (recommended: true)
  * `use_paged_context_fmha`: Enable paged context FMHA (recommended: true)
  * `use_fp8_context_fmha`: Enable `FP8` context FMHA (requires `fp8_kv` or `fp4_kv` quantization)

  The engine auto-selects GEMM plugin settings from your model architecture and quantization type.

  ```yaml theme={"system"}
  build:
    plugin_configuration:
      paged_kv_cache: true
      use_paged_context_fmha: true
      use_fp8_context_fmha: true  # For FP8_KV quantization
  ```
</ParamField>

<ParamField type="object">
  **Optional.** Configuration for speculative decoding with lookahead. For detailed configuration, see [Lookahead decoding](/engines/engine-builder-llm/lookahead-decoding).

  **Fields:**

  * `speculative_decoding_mode`: `LOOKAHEAD_DECODING` (recommended)
  * `lookahead_windows_size`: Window size for speculation (minimum 1)
  * `lookahead_ngram_size`: N-gram size for patterns (minimum 1)
  * `lookahead_verification_set_size`: Verification buffer size (minimum 1)
  * `enable_b10_lookahead`: Enable Baseten's lookahead algorithm

  ```yaml theme={"system"}
  build:
    speculator:
      speculative_decoding_mode: LOOKAHEAD_DECODING
      lookahead_windows_size: 3
      lookahead_ngram_size: 8
      lookahead_verification_set_size: 3
      enable_b10_lookahead: true
  ```
</ParamField>

<ParamField type="number">
  **Optional.** Number of GPUs to use during the build job. Only set this if you encounter errors during the build job. It has no impact once the model reaches the deploying stage. If not set, equals `tensor_parallel_count`.

  ```yaml theme={"system"}
  build:
    num_builder_gpus: 2
  ```
</ParamField>

## Runtime configuration

The `runtime` section configures inference engine behavior.

<ParamField type="number">
  **Optional.** Fraction of GPU memory to reserve for KV cache. Set a value between 0 and 1.

  ```yaml theme={"system"}
  runtime:
    kv_cache_free_gpu_mem_fraction: 0.85
  ```
</ParamField>

<ParamField type="boolean">
  **Optional.** Enable chunked prefilling for long sequences.

  ```yaml theme={"system"}
  runtime:
    enable_chunked_context: true
  ```
</ParamField>

<ParamField type="string">
  **Optional.** Policy for scheduling requests in batches.

  **Options:**

  * `max_utilization`: Maximize GPU utilization (may evict requests)
  * `guaranteed_no_evict`: Guarantee request completion (recommended)

  ```yaml theme={"system"}
  runtime:
    batch_scheduler_policy: guaranteed_no_evict
  ```
</ParamField>

<ParamField type="string">
  **Optional.** Model name returned in API responses.

  ```yaml theme={"system"}
  runtime:
    served_model_name: "Llama-3.3-70B-Instruct"
  ```
</ParamField>

<ParamField type="number">
  **Optional.** Default maximum number of tokens to generate per request when not specified by the client. If not set, the engine uses its own default.

  ```yaml theme={"system"}
  runtime:
    request_default_max_tokens: 4096
  ```
</ParamField>

<ParamField type="number">
  **Optional.** Number of bytes to reserve on host (CPU) memory for KV cache offloading. Set to a high value to enable KV cache offloading from GPU to host memory. Only set this if you need to support longer contexts than GPU memory alone can handle.

  ```yaml theme={"system"}
  runtime:
    kv_cache_host_memory_bytes: 10000000000  # ~10GB host memory for KV cache
  ```
</ParamField>

<ParamField type="number">
  **Optional.** Maximum number of tokens that can be scheduled at once.

  ```yaml theme={"system"}
  runtime:
    total_token_limit: 1000000
  ```
</ParamField>

## Configuration examples

### Llama 3.3 70B

```yaml theme={"system"}
model_name: Llama-3.3-70B-Instruct
resources:
  accelerator: H100:4
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

After `truss push`, the build compiles the model with TensorRT-LLM (typically 10-30 minutes for a 70B model). Once deployed, the model is available at your production endpoint with OpenAI-compatible chat completions.

### Qwen 2.5 32B with lookahead decoding

```yaml theme={"system"}
model_name: Qwen-2.5-32B-Lookahead
resources:
  accelerator: H100:2
  cpu: '2'
  memory: 20Gi
  use_gpu: true
trt_llm:
  build:
    base_model: decoder
    checkpoint_repository:
      source: HF
      repo: "Qwen/Qwen2.5-32B-Instruct"
      revision: main
    max_seq_len: 32768
    max_batch_size: 128
    max_num_tokens: 8192
    quantization_type: fp8_kv
    tensor_parallel_count: 2
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
    served_model_name: "Qwen-2.5-32B-Instruct"
```

After `truss push`, the build compiles with lookahead decoding enabled. Lookahead works best with batch sizes under 32. The configuration above sets `max_batch_size: 128` to allow burst capacity while keeping typical load in the optimal range.

### Small model on L4

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

After `truss push`, the build completes in a few minutes on L4. The deployed model serves chat completions at your production sync URL.

### B200 with `FP4` quantization

```yaml theme={"system"}
model_name: Qwen-2.5-32B-FP4
resources:
  accelerator: B200
  cpu: '2'
  memory: 20Gi
  use_gpu: true
trt_llm:
  build:
    base_model: decoder
    checkpoint_repository:
      source: HF
      repo: "Qwen/Qwen2.5-32B-Instruct"
      revision: main
    max_seq_len: 32768
    max_batch_size: 256
    max_num_tokens: 8192
    quantization_type: fp4_kv
    tensor_parallel_count: 1
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
    served_model_name: "Qwen-2.5-32B-Instruct"
```

## Version overrides

**Optional.** Pin specific component versions to override the backend's current defaults. This is useful for debugging or matching a known-working configuration.

```yaml theme={"system"}
trt_llm:
  version_overrides:
    briton_version: "0.20.0_v0.1.5rc1"
    engine_builder_version: "0.20.0.post8.dev1"
    bei_version: "1.8.7"
```

| Field                    | What it pins                                 |
| ------------------------ | -------------------------------------------- |
| `engine_builder_version` | **Optional.** Engine-Builder-LLM build image |
| `briton_version`         | **Optional.** Briton server image            |
| `bei_version`            | **Optional.** BEI server image               |
| `v2_llm_version`         | **Optional.** BIS-LLM (v2) server image      |

The `engine_builder_version`, `briton_version`, and `bei_version` strings must start with a digit. This rule does not apply to `v2_llm_version`. If unset, the backend inserts the current default at deploy time (**Computed**).

## Validation and troubleshooting

### Common errors

**Error:** `FP8 quantization is only supported on L4, H100, H200, B200`

* **Cause:** Using `FP8` quantization on unsupported GPU.
* **Fix:** Use H100 or newer GPU, or use `no_quant`.

**Error:** `FP4 quantization is only supported on B200`

* **Cause:** Using `FP4` quantization on unsupported GPU.
* **Fix:** Use B200 GPU or `FP8` quantization.

**Error:** `Using fp8 context fmha requires fp8 kv, or fp4 with kv cache dtype`

* **Cause:** Mismatch between quantization and context FMHA settings.
* **Fix:** Use `fp8_kv` quantization or disable `use_fp8_context_fmha`.

**Error:** `Tensor parallelism and GPU count must be the same`

* **Cause:** Mismatch between `tensor_parallel_count` and GPU count.
* **Fix:** Ensure `tensor_parallel_count` matches `accelerator` count.

### Performance tuning

**For lowest latency:**

* Reduce `max_batch_size` and `max_num_tokens`.
* Use `batch_scheduler_policy: guaranteed_no_evict`.
* Consider smaller models or quantization.

**For highest throughput:**

* Increase `max_batch_size` and `max_num_tokens`.
* Use `batch_scheduler_policy: max_utilization`.
* Enable quantization on supported hardware.

**For cost optimization:**

* Use L4 GPUs with `FP8` quantization.
* Choose appropriately sized models.
* Tune `max_seq_len` to your actual requirements.

## Model repository structure

All model sources (S3, GCS, HuggingFace, or tar.gz) must follow the standard HuggingFace repository structure. Files must be in the root directory, similar to running:

```bash theme={"system"}
git clone https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct
```

### Required files

**Model configuration (`config.json`):**

* `max_position_embeddings`: Limits maximum context size (content beyond this is truncated).
* `vocab_size`: Vocabulary size for the model.
* `architectures`: Must include `LlamaForCausalLM`, `MistralForCausalLM`, or similar causal LM architectures. Custom code is typically not read.
* `torch_dtype`: Default inference dtype (`float16` or `bfloat16`). Cannot be a pre-quantized model.

**Model weights (`model.safetensors`):**

* Or: `model.safetensors.index.json` + `model-xx-of-yy.safetensors` (sharded).
* Convert to safetensors if you encounter issues with other formats.
* Cannot be a pre-quantized model. Model must be an `fp16`, `bf16`, or `fp32` checkpoint.

**Tokenizer files (`tokenizer_config.json` and `tokenizer.json`):**

* For maximum compatibility, use "FAST" tokenizers compatible with Rust.
* Cannot contain custom Python code.
* For chat completions: must contain `chat_template`, a Jinja2 template.

### Architecture support

| **Model family** | **Supported architectures**            | **Notes**                                                                                                                                                                                    |
| ---------------- | -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Llama**        | `LlamaForCausalLM`                     | Full support for Llama 3. For Llama 4, use BIS-LLM.                                                                                                                                          |
| **Mistral**      | `MistralForCausalLM`                   | Including v0.3 and Small variants.                                                                                                                                                           |
| **Qwen**         | `Qwen2ForCausalLM`, `Qwen3ForCausalLM` | Including Qwen 2.5 and Qwen 3 series.                                                                                                                                                        |
| **QwenMoE**      | `Qwen3MoEForCausalLM`                  | Specific support for Qwen3MoE.                                                                                                                                                               |
| **Gemma**        | `GemmaForCausalLM`                     | Including Gemma 2 and Gemma 3 series, **`bf16` only**. Gemma uses int8 GEMM kernels that are incompatible with FP8 quantization. Use `no_quant` (BF16) or deploy on BIS-LLM for FP8 support. |

## Best practices

### Model size and GPU selection

| **Model size** | **Recommended GPU** | **Quantization** | **Tensor parallel** |
| -------------- | ------------------- | ---------------- | ------------------- |
| `<8B`          | H100\_40GB / H100   | `FP8_KV`         | 1                   |
| 8B-30B         | H100 / B200         | `FP8` / `FP8_KV` | 1                   |
| 30B-70B        | H100                | `FP8` / `FP8_KV` | 2-4                 |
| `70B+`         | H100 / B200         | `FP8` / `FP4`    | 4-8                 |

### Production recommendations

* Use `quantization_type: fp8_kv` for best performance/accuracy balance.
* Set `max_batch_size` based on your expected traffic patterns.
* Enable `paged_kv_cache` and `use_paged_context_fmha` for optimal performance.

### Development recommendations

* Use `quantization_type: no_quant` for fastest iteration.
* Set smaller `max_seq_len` to reduce build time.
* Use `batch_scheduler_policy: guaranteed_no_evict` for predictable behavior.
