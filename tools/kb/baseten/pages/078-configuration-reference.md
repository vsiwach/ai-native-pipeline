# Configuration reference
Source: https://docs.baseten.co/engines/bei/bei-reference

Complete reference config for BEI and BEI-Bert engines

This reference covers all configuration options for BEI and BEI-Bert deployments. All settings use the `trt_llm` section in `config.yaml`.

## Configuration structure

```yaml theme={"system"}
trt_llm:
  inference_stack: v1  # Always v1 for BEI
  build:
    base_model: encoder | encoder_bert
    checkpoint_repository: {...}
    max_num_tokens: 16384
    quantization_type: no_quant | fp8 | fp4 | fp4_mlp_only
    quantization_config: {...}
    plugin_configuration: {...}
  runtime:
    webserver_default_route: /v1/embeddings | /rerank | /predict
```

## Build configuration

Fields are tagged **Required**, **Optional**, or **Computed**. Computed fields are set by the engine; do not configure them manually.

The `build` section configures model compilation and optimization settings.

<ParamField type="string">
  **Required.** The base model architecture determines which BEI variant to use.

  **Options:**

  * `encoder`: BEI - for causal embedding models (Llama, Mistral, Qwen, Gemma)
  * `encoder_bert`: BEI-Bert - for BERT-based models (BERT, RoBERTa, Jina, Nomic)

  ```yaml theme={"system"}
  build:
    base_model: encoder
  ```
</ParamField>

<ParamField type="object">
  **Required.** Specifies where to find the model checkpoint. Repository must follow the standard HuggingFace structure.

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
    repo: "BAAI/bge-large-en-v1.5"
    revision: main
    runtime_secret_name: hf_access_token  # Optional, for private repos
  ```

  <Note>
    `checkpoint_repository` is the weight source for BEI models, and Baseten mirrors it to the [Baseten Delivery Network](/development/model/bdn) automatically for fast cold starts. Don't add a top-level `weights:` section to a BEI config: `checkpoint_repository` already handles weight loading, so using `weights:` directly is discouraged.
  </Note>
</ParamField>

<ParamField type="number">
  **Optional.** Maximum number of tokens that can be processed in a single batch. BEI defaults to `16384`; BEI-Bert defaults to `8192`. BEI and BEI-Bert run without chunked-prefill for performance reasons. This limits the effective context length to the `max_position_embeddings` value.

  **Range:** 65 to 1048576 (`gt=64, le=1048576` in schema). Use higher values for long context models. Most models use 16384 as default.

  ```yaml theme={"system"}
  build:
    max_num_tokens: 16384
  ```
</ParamField>

<ParamField type="number">
  **Computed.** Not supported for BEI engines. Leave this value unset. BEI automatically sets it and truncates if context length is exceeded.
</ParamField>

<ParamField type="string">
  **Optional.** Specifies the quantization format for model weights. `FP8` quantization maintains accuracy within 1% of `FP16` for embedding models.

  **Options for BEI:**

  * `no_quant`: `FP16`/`BF16` precision
  * `fp8`: `FP8` weights + 16-bit KV cache
  * `fp4`: `FP4` weights + 16-bit KV cache (B200 only)
  * `fp4_mlp_only`: `FP4` MLP weights only (B200 only)

  **Options for BEI-Bert:**

  * `no_quant`: `FP16` precision (only option)

  For detailed quantization guidance, see [Quantization guide](/engines/performance-concepts/quantization-guide).

  ```yaml theme={"system"}
  build:
    quantization_type: fp8
  ```
</ParamField>

<ParamField type="object">
  **Optional.** Configuration for post-training quantization calibration.

  **Fields:**

  * `calib_size`: Size of calibration dataset (64-16384, multiple of 64)
  * `calib_dataset`: HuggingFace dataset for calibration
  * `calib_max_seq_length`: Maximum sequence length for calibration

  ```yaml theme={"system"}
  quantization_config:
    calib_size: 1024
    calib_dataset: "abisee/cnn_dailymail"
    calib_max_seq_length: 1536
  ```
</ParamField>

<ParamField type="object">
  **Computed.** BEI automatically configures optimal TensorRT-LLM plugin settings. Manual configuration is not required or supported.

  **Automatic optimizations:**

  * XQA kernels for maximum throughput
  * Dynamic batching for optimal utilization
  * Memory-efficient attention mechanisms
  * Hardware-specific optimizations

  **Note:** Plugin configuration is only available for Engine-Builder-LLM engine.
</ParamField>

## Runtime configuration

The `runtime` section configures serving behavior.

<ParamField type="string">
  **Optional.** The default API endpoint for the deployment.

  **Options:**

  * `/v1/embeddings`: OpenAI-compatible embeddings endpoint
  * `/rerank`: Reranking endpoint
  * `/predict`: Classification/prediction endpoint

  BEI automatically detects embedding models and sets `/v1/embeddings`. Classification models default to `/predict`.

  ```yaml theme={"system"}
  runtime:
    webserver_default_route: /v1/embeddings
  ```
</ParamField>

<ParamField type="number">
  **Computed.** Available but has no effect for BEI embedding models, which do not use a KV cache. Only relevant for generative (decoder) models.
</ParamField>

<ParamField type="boolean">
  **Computed.** Available but has no effect for BEI embedding models. Only relevant for generative (decoder) models.
</ParamField>

<ParamField type="string">
  **Computed.** Available but has no effect for BEI embedding models. Only relevant for generative (decoder) models.
</ParamField>

## HuggingFace model repository structure

All model sources (S3, GCS, HuggingFace, or tar.gz) must follow the standard HuggingFace repository structure. Files must be in the root directory, similar to running:

```bash theme={"system"}
git clone https://huggingface.co/michaelfeil/bge-small-en-v1.5
```

### Model configuration

**config.json**

* `max_position_embeddings`: Limits maximum context size (content beyond this is truncated)
* `id2label`: Required dictionary mapping IDs to labels for classification models.
  * **Note**: Needs to have len of the shape of the last dense layer. Each dense output needs a `name` for the json response.
* `architecture`: Must be `ModelForSequenceClassification` or similar (cannot be `ForCausalLM`)
  * **Note**: Remote code execution is not supported; architecture is inferred automatically
* `torch_dtype`: Default inference dtype (BEI-Bert: always `fp16`, BEI: `float16`, `bfloat16`)
  * **Note**: We don't support `pre-quantized` loading, meaning your weights need to be `float16`, `bfloat16` or `float32` for all engines.
* `quant_config`: Not allowed, as no `pre-quantized` weights.

#### Model weights

**model.safetensors** (preferred)

* Or: `model.safetensors.index.json` + `model-xx-of-yy.safetensors` (sharded)
* **Note**: Convert to safetensors if you encounter issues with other formats

#### Tokenizer files

**tokenizer\_config.json** and **tokenizer.json**

* Must be "FAST" tokenizers compatible with Rust
* Typically cannot contain custom Python code, will be unread.

#### Embedding model files (sentence-transformers)

**1\_Pooling/config.json**

* Required for embedding models to define pooling strategy

**modules.json**

* Required for embedding models
* Shows available pooling layers and configurations

At build time, BEI reads pooling mode from `modules.json` and `1_Pooling/config.json` and maps it to one of the modes below.

| Flag in `1_Pooling/config.json`  | Pooling mode            | BEI | BEI-Bert |
| -------------------------------- | ----------------------- | --- | -------- |
| `pooling_mode_cls_token: true`   | CLS token (first token) | ✅   | ✅        |
| `pooling_mode_mean_tokens: true` | Mean tokens             | ✅   | ✅        |
| `pooling_mode_lasttoken: true`   | Last token              | ✅   | ✅        |

If either file is missing on an embedding checkpoint, the build fails with a clear error naming the missing path. Sequence classification and reranking models skip pooling detection and use the classification head instead.

### Pooling layer support

| **Engine**   | **Classification Layers**  | **Pooling Types**                             | **Notes**                |
| ------------ | -------------------------- | --------------------------------------------- | ------------------------ |
| **BEI**      | 1 layer maximum            | Last token, first token                       | Limited pooling options  |
| **BEI-Bert** | Multiple layers or 1 layer | Last token, first token, mean, SPLADE pooling | Advanced pooling support |

## Throughput benchmarks

Measured against TEI and vLLM on the same hardware. Token throughput uses 500 tokens per request; request throughput uses 5 tokens per request. For the full methodology, see [Run Qwen3 Embedding on NVIDIA Blackwell GPUs](https://www.baseten.co/blog/run-qwen3-embedding-on-nvidia-blackwell-gpus/#bei-provides-the-fastest-embeddings-inference-on-b200s).

| Framework | Precision | GPU  | Max tokens/s | Max requests/s |
| --------- | --------- | ---- | ------------ | -------------- |
| TEI       | FP16      | H100 | 34,055       | 824.25         |
| BEI-Bert  | FP16      | H100 | 36,520       | 841.05         |
| vLLM      | BF16      | H100 | 36,625       | 155.23         |
| BEI       | BF16      | H100 | 47,549       | 761.44         |
| BEI       | FP8       | H100 | 77,107       | 855.96         |
| BEI       | FP8       | B200 | 121,443      | 1,310.52       |

## Quantization impact

| Quantization   | Speed improvement | Memory reduction | Accuracy impact |
| -------------- | ----------------- | ---------------- | --------------- |
| FP16/BF16 vLLM | Baseline          | None             | None            |
| FP16/BF16 BEI  | 1.3x              | None             | None            |
| FP8 BEI        | 2x                | 50%              | \~1%            |
| FP4 BEI        | 3.5x              | 75%              | 1-2%            |

## Hardware support

| GPU        | BEI  | BEI-Bert | Recommended for            |
| ---------- | ---- | -------- | -------------------------- |
| L4         | Full | Full     | Cost-effective deployments |
| A10G, A100 | Full | Full     | Legacy support             |
| T4         | No   | Full     | Legacy support             |
| H100       | Full | Full     | Maximum performance        |
| B200       | Full | Full     | `FP4` quantization         |

## Complete configuration examples

### BEI with `FP8` quantization (embedding model)

```yaml theme={"system"}
model_name: BEI-BGE-Large-FP8
resources:
  accelerator: H100
  use_gpu: true
trt_llm:
  build:
    base_model: encoder
    checkpoint_repository:
      source: HF
      repo: "Qwen/Qwen3-Embedding-8B"
      revision: main
    max_num_tokens: 16384
    quantization_type: fp8
    quantization_config:
      calib_size: 1536
      calib_dataset: "abisee/cnn_dailymail"
      calib_max_seq_length: 1536
    # plugin_configuration is auto-configured for BEI models.
    # Encoder models disable paged_kv_cache and use_paged_context_fmha automatically.
  runtime:
    webserver_default_route: /v1/embeddings
```

### BEI-Bert for small BERT model

```yaml theme={"system"}
model_name: BEI-Bert-MiniLM-L6
resources:
  accelerator: L4
  use_gpu: true
trt_llm:
  build:
    base_model: encoder_bert
    checkpoint_repository:
      source: HF
      repo: "sentence-transformers/all-MiniLM-L6-v2"
      revision: main
    max_num_tokens: 8192
    quantization_type: no_quant
    # plugin_configuration is auto-configured for BEI-Bert models.
    # paged_kv_cache and use_paged_context_fmha are disabled automatically.
  runtime:
    webserver_default_route: /v1/embeddings
```

### BEI for reranking model

```yaml theme={"system"}
model_name: BEI-BGE-Reranker
resources:
  accelerator: H100
  use_gpu: true
trt_llm:
  build:
    base_model: encoder
    checkpoint_repository:
      source: HF
      repo: "BAAI/bge-reranker-large"
      revision: main
    max_num_tokens: 16384
    quantization_type: fp8
    quantization_config:
      calib_size: 1024
      calib_dataset: "abisee/cnn_dailymail"
      calib_max_seq_length: 2048
  runtime:
    webserver_default_route: /rerank
```

### BEI-Bert for classification model

```yaml theme={"system"}
model_name: BEI-Bert-Language-Detection
resources:
  accelerator: L4
  use_gpu: true
trt_llm:
  build:
    base_model: encoder_bert
    checkpoint_repository:
      source: HF
      repo: "papluca/xlm-roberta-base-language-detection"
      revision: main
    max_num_tokens: 8192
    quantization_type: no_quant
  runtime:
    webserver_default_route: /predict
```

### BEI-Bert for code embeddings (Jina)

```yaml theme={"system"}
model_name: BEI-Bert-Jina-Code
resources:
  accelerator: H100
  use_gpu: true
trt_llm:
  build:
    base_model: encoder_bert
    checkpoint_repository:
      source: HF
      repo: "jinaai/jina-embeddings-v2-base-code"
      revision: main
    max_num_tokens: 8192
    quantization_type: no_quant
  runtime:
    webserver_default_route: /v1/embeddings
    kv_cache_free_gpu_mem_fraction: 0.9
    batch_scheduler_policy: guaranteed_no_evict
```

### BEI-Bert for bidirectional Qwen2 (long sequences)

```yaml theme={"system"}
model_name: BEI-Bert-GTE-Qwen-1.5B
resources:
  accelerator: L4
  use_gpu: true
trt_llm:
  build:
    base_model: encoder_bert
    checkpoint_repository:
      source: HF
      repo: "Alibaba-NLP/gte-Qwen2-1.5B-instruct"
      revision: main
    max_num_tokens: 8192
    quantization_type: no_quant
  runtime:
    webserver_default_route: /v1/embeddings
    kv_cache_free_gpu_mem_fraction: 0.85
    batch_scheduler_policy: guaranteed_no_evict
```

## Common configuration errors

**Warning:** Briton logs: "Compling `encoder` with a kv-cache dtype is a alpha feature. This may fail."

* **Cause:** Using a KV quantization type (`fp8_kv`, `fp4_kv`) with an encoder model. Encoders do not use a KV cache, so these variants are alpha and may fail the build.
* **Fix:** Use `fp8` or `no_quant` instead.

**Error:** `FP8 quantization is only supported on L4, H100, H200, B200`

* **Cause:** Using `FP8` quantization on unsupported GPU.
* **Fix:** Use H100 or newer GPU, or use `no_quant`.

**Error:** `FP4 quantization is only supported on B200`

* **Cause:** Using `FP4` quantization on unsupported GPU.
* **Fix:** Use B200 GPU or `FP8` quantization.
