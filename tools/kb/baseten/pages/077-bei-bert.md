# BEI-Bert
Source: https://docs.baseten.co/engines/bei/bei-bert

Bidirectional encoder embeddings with cold-start optimization

BEI-Bert is a variant of Baseten Embeddings Inference for BERT-family architectures. It runs at `FP16` or `BF16`, optimizes cold-start latency, and supports bidirectional attention for sub-4B-parameter encoders.

<Note>
  **Bidirectional attention** means each token in the input can attend to every other token, in both directions. BERT-family encoders use this pattern, which generally produces better embeddings because each token sees the full context. Causal models like GPT use the opposite pattern: each token attends only to earlier tokens, never to later ones. Some Qwen and Llama checkpoints (the `*Bidirectional` model variants listed below) are causal LLMs adapted to run in bidirectional mode specifically for embedding use.
</Note>

## BEI vs BEI-Bert

Both variants run on the same engine binary. Pick the variant that matches your base architecture.

| Feature      | BEI-Bert                             | BEI                               |
| ------------ | ------------------------------------ | --------------------------------- |
| Architecture | BERT-based (bidirectional)           | Causal (unidirectional)           |
| Precision    | `FP16` (16-bit)                      | `BF16`, `FP16`, `FP8`, `FP4`      |
| Cold-start   | Optimized for fast initialization    | Standard startup                  |
| Quantization | Not supported                        | `FP8`, `FP4` supported            |
| Memory usage | Lower for small models               | Higher or equal                   |
| Throughput   | 600-900 embeddings/sec               | 800-1400 embeddings/sec           |
| Best for     | Small BERT models, accuracy-critical | Large models, throughput-critical |

## When to use BEI-Bert

Choose BEI-Bert when any of these apply:

* **BERT-family base architecture**: `BertModel`, `RobertaModel`, `ModernBertModel`, `XLMRobertaModel`, or a `*Bidirectional` adapted checkpoint.
* **Cold-start matters**: first-request latency is critical for your traffic shape.
* **Small to medium models**: under 4B parameters where `FP8`/`FP4` quantization isn't needed.
* **16-bit precision**: workloads where `FP16` accuracy is preferred over quantized throughput.
* **Token-level classification**: NER and other `/predict_tokens` endpoints run on BEI-Bert only.

For models over 4B parameters, causal embedders, or workloads that need `FP8`/`FP4` quantization, use BEI. See the [BEI overview](/engines/bei/overview).

## Supported model families

BEI-Bert runs the following base architectures: `BertModel`, `RobertaModel`, `ModernBertModel`, `XLMRobertaModel`, `Gemma3Bidirectional`, `Qwen2Bidirectional`, `Qwen3Bidirectional`, `LLama3Bidirectional`.

### Sentence-transformers

The most common BERT-based embedding models, optimized for semantic similarity.

* `sentence-transformers/all-MiniLM-L6-v2` (384D, 22M params)
* `sentence-transformers/all-mpnet-base-v2` (768D, 110M params)
* `sentence-transformers/multi-qa-mpnet-base-dot-v1` (768D, 110M params)

### Jina AI

Jina's BERT-based models for general and code-specific domains.

* `jinaai/jina-embeddings-v2-base-en` (512D, 137M params)
* `jinaai/jina-embeddings-v2-base-code` (512D, 137M params)
* `jinaai/jina-embeddings-v2-base-es` (512D, 137M params)

### Nomic AI

Nomic's models with specialized training for text and code.

* `nomic-ai/nomic-embed-text-v1.5` (768D, 137M params)
* `nomic-ai/nomic-embed-code-v1.5` (768D, 137M params)

### Alibaba GTE and Qwen (bidirectional)

Multilingual models with instruction-tuning and long-context support.

* `Alibaba-NLP/gte-Qwen2-7B-instruct` (top-ranked multilingual)
* `Alibaba-NLP/gte-Qwen2-1.5B-instruct` (cost-effective alternative)
* `intfloat/multilingual-e5-large-instruct`

### Bidirectional LLM variants

Some Qwen and Llama checkpoints run in **bidirectional mode**: each token attends to the full input, which often improves embedding quality over causal pooling.

* **Qwen2Bidirectional**: `Alibaba-NLP/gte-Qwen2-7B-instruct`
* **Qwen3Bidirectional**: `voyageai/voyage-4-nano` ([contact Baseten](mailto:support@baseten.co) for deploy config)
* **Llama3Bidirectional**: `nvidia/llama-embed-nemotron-8b`

Set `base_model: encoder_bert`. The build applies bidirectional attention automatically.

#### Checkpoint requirements

BEI-Bert builds standard Hugging Face checkpoints only. Repos that require `trust_remote_code` fail at build time. Pin `checkpoint_repository.revision` when the model maintainer publishes a compatible config on a non-default branch.

For `voyageai/voyage-4-nano`, the default Hugging Face branch is not compatible with BEI-Bert. [Contact your Baseten representative](mailto:support@baseten.co) for the current `checkpoint_repository` settings before you deploy.

### Reranking

BEI-Bert runs cross-encoder rerankers through `/rerank`. Recommended:

* `BAAI/bge-reranker-large` (XLM-RoBERTa)
* `BAAI/bge-reranker-base` (XLM-RoBERTa base)
* `Alibaba-NLP/gte-multilingual-reranker-base`
* `Alibaba-NLP/gte-reranker-modernbert-base`

### Classification

BEI-Bert runs sequence classifiers through `/predict`. The classifier head needs an `id2label` dictionary in the Hugging Face config. Recommended:

* `SamLowe/roberta-base-go_emotions` (sentiment)
* `papluca/xlm-roberta-base-language-detection` (language ID)

### Named entity recognition

Token-level entity classification routes to `/predict_tokens` and runs on BEI-Bert only. Recommended:

* `dslim/bert-base-NER-uncased` ([Truss example](https://github.com/basetenlabs/truss-examples/tree/main/custom-server/BEI-Bert-dslim-bert-base-ner-uncased))
* `tanaos/tanaos-NER-v1`

For the full request/response format and Python example, see [Named entity recognition](/engines/bei/ner).

## Model selection by constraint

Choose based on your primary constraint:

**Balanced cost and performance:**

* `Alibaba-NLP/gte-Qwen2-7B-instruct`: instruction-tuned, ranked #1 for multilingual.
* `Alibaba-NLP/gte-Qwen2-1.5B-instruct`: 1/5 the size, still top-tier.
* `Snowflake/snowflake-arctic-embed-m-v2.0`: multilingual-optimized, MRL support.

**Lightweight (under 500M params):**

* `google/embeddinggemma-300m`: 300M params, 100+ languages.
* `nomic-ai/nomic-embed-text-v1.5`: 137M, minimal latency.
* `sentence-transformers/all-MiniLM-L6-v2`: 22M, legacy standard.

**Specialized:**

* Code: `jinaai/jina-embeddings-v2-base-code`.
* Long sequences: `Alibaba-NLP/gte-large-en-v1.5`.
* Reranking: `BAAI/bge-reranker-large`, `Alibaba-NLP/gte-reranker-modernbert-base`.

## Minimal configuration

BEI-Bert deployments set `base_model: encoder_bert` and `quantization_type: no_quant`. Pull weights from Hugging Face by default.

```yaml theme={"system"}
trt_llm:
  inference_stack: v1
  build:
    base_model: encoder_bert
    checkpoint_repository:
      source: HF
      repo: "sentence-transformers/all-MiniLM-L6-v2"
    quantization_type: no_quant
  runtime:
    webserver_default_route: /v1/embeddings
```

For the full schema, including `max_num_tokens`, GPU support, and complete examples for sentence-transformers, Jina, Nomic, and bidirectional LLM variants, see the [BEI configuration reference](/engines/bei/bei-reference).

## Related

* [BEI overview](/engines/bei/overview): Causal embeddings, reranking, and OpenAI-compatible inference.
* [BEI configuration reference](/engines/bei/bei-reference): Full `trt_llm` schema, pooling matrix, hardware support, and complete configuration examples.
* [Named entity recognition](/engines/bei/ner): `/predict_tokens` request and response format.
* [Embedding examples](/examples/bei): Concrete deployment examples.
* [Performance Client](/inference/performance-client): High-throughput batch inference for embeddings and reranking.
