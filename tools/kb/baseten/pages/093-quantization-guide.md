# Quantization guide
Source: https://docs.baseten.co/engines/performance-concepts/quantization-guide

FP8 and FP4 trade-offs and hardware requirements for all engines

*Quantization* trades precision for speed and memory efficiency. This guide covers Baseten's supported formats, hardware requirements, and model-specific recommendations.

Two facts bound a format choice: which GPU families run it, and how much weight memory it saves. The matrix below shows both at once. Each row is a format, the columns mark which GPUs support it, and the bar on the right is its weight footprint measured against `FP16`. `FP8` runs everywhere and halves the footprint, while the `FP4` formats reach a quarter but require a B200.

<QuantizationMatrix />

A ✓ marks the GPU families that run a format, so you can rule out the ones your hardware cannot run before weighing memory. Each bar divides the format's bit width by the 16-bit `FP16` baseline: 8-bit formats land at half, 4-bit formats at a quarter. The bar measures model weights only. It excludes KV cache and activation memory, and it shows neither end-to-end memory savings nor any accuracy trade-off, both of which depend on the model and workload. `FP4_MLP_ONLY` is mixed precision, so its bar sits between `FP8` and `FP4` rather than at a single clean ratio.

## Quantization options

Quantization type availability depends on the engine and GPU.

<EnginesSymbolLegend />

### Engine support

| **Quantization**       | [**BIS-LLM**](/engines/bis-llm/overview) | [**Engine-Builder-LLM**](/engines/engine-builder-llm/overview) | [**BEI**](/engines/bei/overview) |
| ---------------------- | ---------------------------------------- | -------------------------------------------------------------- | -------------------------------- |
| `FP8`                  | ✅                                        | ✅                                                              | ✅                                |
| `FP8_KV`               | ✅                                        | ✅                                                              | ⚠️                               |
| `FP4`                  | ✅                                        | ✅                                                              | ⚠️                               |
| `FP4_KV`               | ✅                                        | ✅                                                              | ⚠️                               |
| `FP4_MLP_ONLY`         | ✅                                        | ✅                                                              | ✅                                |
| `no_quant`             | ✅                                        | ✅                                                              | ✅                                |
| `INT8` / `SmoothQuant` | ❌                                        | ✅                                                              | ❌                                |

`_KV` quantization formats (`FP8_KV`, `FP4_KV`) store compressed KV cache state. Encoder models (BEI, BEI-Bert) do not use a decoder-style KV cache, so these formats are not applicable. The ⚠️ cells above mark that limitation, not partial support.

`INT8` and `SmoothQuant` quantization types are supported on Engine-Builder-LLM (v1) but rejected on BIS-LLM (v2). The v2 build raises an error at build time: use `FP8` or `FP4` instead, which provide better accuracy-to-compression ratios on modern GPUs.

### `no_quant` and pre-quantized checkpoints

Setting `quantization_type: no_quant` tells the engine to skip post-training quantization and use the checkpoint's native precision. This is the right choice in two scenarios:

1. **Unquantized FP16/BF16 checkpoints.** The engine uses the model's native dtype without any calibration step. This is the default for development and accuracy-critical deployments.

2. **Pre-quantized ModelOpt checkpoints.** Some Hugging Face repos ship with NVIDIA ModelOpt quantization already applied (indicated by an `hf_quant_config.json` file in the repo). For these checkpoints, set `quantization_type: no_quant`. The engine detects the ModelOpt config and applies the pre-baked quantization automatically. Attempting to re-quantize a ModelOpt checkpoint with a different `quantization_type` causes a build error.

**Example: deploying a pre-quantized ModelOpt checkpoint on BIS-LLM**

```yaml theme={"system"}
trt_llm:
  inference_stack: v2
  build:
    checkpoint_repository:
      source: HF
      repo: "nvidia/DeepSeek-V3.1-NVFP4"
    quantization_type: no_quant  # ModelOpt quantization detected from hf_quant_config.json
```

Non-ModelOpt pre-quantized checkpoints (for example, GPTQ or AWQ safetensors) are not supported. The build rejects them with an error.

### GPU support

| **GPU type** | `FP8` | `FP8_KV` | `FP4` | `FP4_KV` | `FP4_MLP_ONLY` |
| ------------ | ----- | -------- | ----- | -------- | -------------- |
| **L4**       | ✅     | ✅        | ❌     | ❌        | ❌              |
| **H100**     | ✅     | ✅        | ❌     | ❌        | ❌              |
| **H200**     | ✅     | ✅        | ❌     | ❌        | ❌              |
| **B200**     | ✅     | ✅        | ✅     | ✅        | ✅              |

## Model recommendations

Some model families have specific quantization requirements that affect accuracy.

### Qwen2 models

Qwen2 retains QKV projection bias (attention bias), while Qwen3, Llama3, Llama2, and most other models remove it. This makes Qwen2 sensitive to symmetric KV cache quantization, so `FP8_KV` causes quality degradation. Use regular `FP8` instead and increase calibration size to 1024 or greater for better accuracy.

### Llama models

Llama variants work well with `FP8_KV` and standard calibration sizes (1024-1536). For B200 deployments, use `FP4_MLP_ONLY` for the best balance of speed and quality.

### BEI models (embeddings)

Use `FP8` for causal embedding models. Skip quantization for smaller models since the overhead isn't worth the minimal benefit and Bert is not supported. BEI doesn't support `FP8_KV` or other `_KV` formats because encoder models have no KV cache to quantize.

## Calibration

Quantization requires calibration data to determine optimal scaling factors. Larger models generally need more calibration samples.

### Calibration datasets

The default dataset is `cnn_dailymail` (general news text). For specialized models, or fine-tunes specific to a chat template, use domain-specific datasets when available.
For using a custom dataset, reference the huggingface name under `calib_dataset`, and make sure the dataset has a `train` split with a `text`/`messages` column.

When using the `messages` column, we require the tokenizer of your model to have a `apply_chat_template()` function on which we can apply `apply_chat_template(row["messages"]) for row in rows`.
If you want to use a dataset without preprocessing, you can provide a `text` column.

For chat-based calibration with thinking , we open-sourced [`baseten/quant_calibration_dataset_v1`](https://huggingface.co/datasets/baseten/quant_calibration_dataset_v1), to showcase an example.

### Calibration configuration

```yaml theme={"system"}
quantization_config:
  calib_size: 768                    # Number of samples
  calib_dataset: "abisee/cnn_dailymail"  # Dataset name
  calib_max_seq_length: 1024          # Max sequence length
```

Increase `calib_size` for larger models. Use domain-specific datasets when available for better accuracy on specialized tasks.

## Hardware requirements

`FP4` quantization requires B200 GPUs. `FP8` runs on L4 and above.

| **Quantization** | **Minimum GPU** | **Recommended GPU** | **Memory reduction** |
| ---------------- | --------------- | ------------------- | -------------------- |
| `FP16`/`BF16`    | A100            | H100                | None                 |
| `FP8`            | L4              | H100                | \~50%                |
| `FP8_KV`         | L4              | H100                | \~60%                |
| `FP4`            | B200            | B200                | \~75%                |
| `FP4_KV`         | B200            | B200                | \~80%                |

### Configuration examples

**Engine-Builder-LLM:**

```yaml theme={"system"}
trt_llm:
  build:
    base_model: decoder
    quantization_type: fp8
    quantization_config:
      calib_size: 1024
```

**BIS-LLM:**

```yaml theme={"system"}
trt_llm:
  inference_stack: v2
  build:
    quantization_type: fp8
    quantization_config:
      calib_size: 1024
  runtime:
    max_seq_len: 32768
```

**BEI:**

```yaml theme={"system"}
trt_llm:
  build:
    base_model: encoder
    quantization_type: fp8
    max_num_tokens: 16384
```

Set `quantization_type` in the build section and add `quantization_config` to customize calibration. BIS-LLM uses `inference_stack: v2` while Engine-Builder-LLM uses `base_model: decoder`.

## Best practices

### When to use quantization

Use `FP8` for production deployments to achieve cost-effective scaling. For memory-constrained environments, `FP8_KV` or `FP4` variants provide additional memory reduction. Quantization becomes essential for models over 15B parameters where memory and cost savings are significant.

### When to avoid quantization

Skip quantization when maximum accuracy is critical. Use `FP16`/`BF16` instead. Small models under 8B parameters see minimal benefit from quantization. BEI-Bert models don't support quantization at all. During research and development, `FP16` provides faster iteration without calibration overhead.

### Optimization tips

Use calibration datasets that match your domain for best accuracy. Test quantized models with your specific data before production deployment. Monitor the accuracy vs. performance trade-off and consider your hardware constraints when selecting quantization type.

## Related

* [Configure Engine-Builder-LLM quantization](/engines/engine-builder-llm/engine-builder-config): Dense model build options.
* [Configure BIS-LLM quantization](/engines/bis-llm/bis-llm-config): MoE model build options.
* [Configure BEI quantization](/engines/bei/bei-reference): Embedding model build options.
