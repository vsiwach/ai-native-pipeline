# LoRA support
Source: https://docs.baseten.co/engines/engine-builder-llm/lora-support

Multi-LoRA adapters for Engine-Builder-LLM engine

Engine-Builder-LLM supports multi-LoRA deployments with runtime adapter switching. Share base model weights across fine-tuned variants and switch adapters without redeployment.

## Overview

Deploy multiple LoRA adapters on a single base model and switch between them at inference time. The engine shares base model weights across all adapters for memory efficiency.

## Configuration

### Basic LoRA configuration

```yaml theme={"system"}
model_name: Qwen2.5-Coder-LoRA
resources:
  accelerator: H100
  cpu: '2'
  memory: 20Gi
  use_gpu: true
trt_llm:
  build:
    base_model: decoder
    checkpoint_repository:
      source: HF
      repo: "Qwen/Qwen2.5-Coder-1.5B-Instruct"
      revision: "2e1fd397ee46e1388853d2af2c993145b0f1098a"
    lora_adapters:
      lora1:
        repo: "ai-blond/Qwen-Qwen2.5-Coder-1.5B-Instruct-lora"
        revision: "9cde18d8ed964b0519fb481cca6acd936b2ca811"
        source: "HF"
    lora_configuration:
      max_lora_rank: 16
  runtime:
    served_model_name: "Qwen2.5-Coder-base"
```

## Limitations

* **Same rank and same modules**: All adapters in one deployment must share the same rank and target modules.
* **Build time availability**: The engine relies on numpy-style weights. These need to be pre-converted during deployment and distributed to each replica. For Engine-Builder-LLM, these repos must be known ahead of time.
* **Inference performance**: If you're using only one LoRA adapter, merging the adapter into the base weights provides better performance. Additional LoRA adapters add complexity to kernel selection and fundamentally increase flops.

## LoRA adapter configuration

### Adapter repository structure

LoRA adapters must follow the standard HuggingFace repository structure:

```
adapter-repo/
├── adapter_config.json
├── adapter_model.safetensors
└── README.md
```

### Required files

**adapter\_config.json**

```yaml theme={"system"}
  # same base model for all configs 
  "base_model_name_or_path": "Qwen/Qwen2.5-Coder-1.5B-Instruct", 
  # same target modules among all lora adapters 
  "target_modules": [
    "attn_q",
    "attn_k", 
    "attn_v",
    "attn_dense",
    "mlp_h_to_4h",
    "mlp_4h_to_h",
    "mlp_gate"
  ],
  # same rank among all lora adapters
  "r": 16
```

**adapter\_model.safetensors**

* The LoRA adapter weights in safetensors format.

<Note>
  You don't create or upload any `.npy` files. The engine builder converts your adapter into its internal format (`model.lora_weights.npy`, `model.lora_config.npy`) server-side at build time, deriving the rank and target modules from `adapter_config.json`. Supply a standard Hugging Face adapter repo (`adapter_config.json` plus `adapter_model.safetensors`).
</Note>

## Build configuration options

### `lora_adapters`

Dictionary of LoRA adapters to load during build. Adapter names must match the pattern `^[a-zA-Z0-9_\-\.:]+$`: letters, digits, underscores, hyphens, dots, and colons only.

```yaml theme={"system"}
lora_adapters:
  adapter_name:
    repo: "username/model-name"
    revision: "main"
    source: "HF"  # or "GCS", "S3", "AZURE"
```

### `max_lora_rank`

Maximum LoRA rank for all adapters. Default: **64**. Set this to exactly the rank `r` you use across all adapters. A higher value wastes memory; a lower value truncates weights.

```yaml theme={"system"}
max_lora_rank: 16  # Match the r value in your adapter_config.json
```

### `lora_configuration`

LoRA-specific configuration nested under `build`:

```yaml theme={"system"}
lora_configuration:
  max_lora_rank: 16
  lora_target_modules: []  # Auto-detected from adapter_config.json
```

**Fields:**

* `max_lora_rank`: Maximum LoRA rank across all adapters. Default: 64.
* `lora_target_modules`: Target modules for LoRA. Usually auto-detected from adapter config.

## Engine inference configuration

The model parameter in OpenAI-format requests selects which adapter to use. For the above example, valid model names are `Qwen2.5-Coder-base` or `lora1`.

This lets you select different adapters at runtime through the OpenAI client.

## Related

* [Engine-Builder-LLM overview](/engines/engine-builder-llm/overview): Main engine documentation.
* [Engine-Builder-LLM configuration](/engines/engine-builder-llm/engine-builder-config): Complete reference config.
* [Custom engine builder](/engines/engine-builder-llm/custom-engine-builder): Custom model.py implementation.
* [Quantization guide](/engines/performance-concepts/quantization-guide): Performance optimization.
