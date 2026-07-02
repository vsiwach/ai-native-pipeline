# Overview
Source: https://docs.baseten.co/engines/index

Inference engines for embeddings, dense LLMs, MoE models, and Enterprise serving

Baseten engines optimize model inference for specific architectures using [TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM). All engines mirror build artifacts to the [Baseten Delivery Network](/development/model/bdn) automatically.

* **[BEI](/engines/bei/overview):** Embedding, reranking, and classification models on causal architectures with `FP8` and `FP4` quantization.
* **[BEI-Bert](/engines/bei/bei-bert):** Bidirectional BEI variant tuned for BERT-family encoders and cold-start-sensitive models under 4B parameters.
* **[Engine-Builder-LLM](/engines/engine-builder-llm/overview):** Dense text generation for Llama, Qwen, Mistral, and Gemma with lookahead decoding and multi-LoRA support.
* **[BIS-LLM](/engines/bis-llm/overview):** MoE and Enterprise serving with KV-aware routing, disaggregated prefill/decode, and Eagle/MTP speculation.

## Choose an engine

Pick the row below that matches what you're deploying. Cost, quality, and latency targets drive later choices (GPU, quantization, autoscaling) inside that engine.

* **Embedding, reranking, classification, or NER models:** use [BEI](/engines/bei/overview) for decoder embedders (`Qwen3-Embedding`, `BAAI/bge`, `LlamaForSequenceClassification`) or [BEI-Bert](/engines/bei/bei-bert) for BERT-family encoders (`BERT`, `ModernBERT`, `EuroBERT`, `XLM-RoBERTa`). NER lives on [`BEI-Bert /predict_tokens`](/engines/bei/ner).
* **Dense text-generation LLMs** (`Llama 3` or `4`, `Qwen 3` or `3.5`, `Mistral`, `Gemma`, `Phi`, `GPT-OSS-20B`): use [Engine-Builder-LLM](/engines/engine-builder-llm/overview), with [lookahead decoding](/engines/engine-builder-llm/lookahead-decoding) and [multi-LoRA](/engines/engine-builder-llm/lora-support) available.
* **MoE models** (`GLM 5.x`, `Kimi K2.5` or `K2.6`, `DeepSeek V3`, `R1`, or `V4`, `MiniMax 2.5`, `Qwen3 MoE`, `GPT-OSS-120B`) **or workloads that need KV-cache-aware routing or disaggregated prefill/decode:** use [BIS-LLM](/engines/bis-llm/overview). Currently a co-engineering pilot.
* **Speech, image, video, or custom Python models:** ship a custom Truss. Browse [model examples](/examples/overview) for Whisper, Orpheus, Flux, and other pre-built deployments, or see [build your first model](/development/model/build-your-first-model) for custom inference logic.

If your workload doesn't fit one of the rows above (custom architectures, hybrid pipelines, BIS-LLM pilot access, sizing for unusual traffic shapes), email [support@baseten.co](mailto:support@baseten.co) and an engineer will route you.

## Performance and operations

* [Quantization guide](/engines/performance-concepts/quantization-guide): `FP8` and `FP4` trade-offs, GPU support, and per-engine options.
* [Autoscaling engines](/engines/performance-concepts/autoscaling-engines): Token-based and request-based scaling for engine deployments.
* [Cloud storage deployment](/engines/performance-concepts/cloud-storage-deployment): Deploy engines from S3 or GCS instead of Hugging Face.
* [Specialized model examples](/examples/overview): Pre-built Truss examples for Whisper, Orpheus, Flux, and other dedicated deployments.

## Compare engines

<EnginesSymbolLegend />

| Feature                              | BIS-LLM | Engine-Builder-LLM | BEI | BEI-Bert | Notes                                                                            |
| ------------------------------------ | ------- | ------------------ | --- | -------- | -------------------------------------------------------------------------------- |
| **Quantization**                     | ✅       | ✅                  | ✅   | ❌        | BEI-Bert: `FP16`/`BF16` only.                                                    |
| **KV quantization**                  | ✅       | ✅                  | ⚠️  | ⚠️       | `FP8_KV`, `FP4_KV` supported.                                                    |
| **Lookahead decoding**               | ❌       | ✅                  | ❌   | ❌        | Engine-Builder-LLM (v1) only; BIS-LLM uses MTP/Eagle/N-gram speculation instead. |
| **Self-serviceable**                 | 🔒      | ✅                  | ✅   | ✅        | BIS-LLM requires Enterprise; other engines are self-serve.                       |
| **KV-routing**                       | 🔒      | ❌                  | ❌   | ❌        | BIS-LLM only.                                                                    |
| **Disaggregated serving**            | 🔒      | ❌                  | ❌   | ❌        | BIS-LLM Enterprise.                                                              |
| **Tool calling & structured output** | ✅       | ✅                  | ❌   | ❌        | Function calling support.                                                        |
| **Classification models**            | ❌       | ❌                  | ✅   | ✅        | Sequence classification.                                                         |
| **Embedding models**                 | ❌       | ❌                  | ✅   | ✅        | Embedding generation.                                                            |
| **Mixture-of-experts**               | ✅       | ⚠️ (Qwen3MoE only) | ❌   | ❌        | MoE models like `DeepSeek-R1`.                                                   |
| **MTP / Eagle / N-gram speculation** | 🔒      | ❌                  | ❌   | ❌        | v2 speculative decoding with `speculative_config`.                               |
| **HTTP request cancellation**        | ✅       | ⚠️                 | ✅   | ✅        | Engine-Builder-LLM: within the first 10ms only.                                  |
| **MultiModal Inputs**                | 🔒      | ❌                  | ⚠️  | ❌        | Selected architectures only.                                                     |
