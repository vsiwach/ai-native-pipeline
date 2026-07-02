# Overview
Source: https://docs.baseten.co/engines/bei/overview

Production-grade embeddings, reranking, and classification models

Baseten Embeddings Inference (BEI) serves embedding, classification, and reranking models on TensorRT-LLM, with sub-millisecond response times and up to 1,400 client embeddings per second on H100. Builds mirror to the [Baseten Delivery Network](/development/model/bdn) so cold starts stay fast.

## Inference stack

BEI runs on the v1 inference stack. In `config.yaml`, set `inference_stack: v1` and `base_model: encoder` for causal architectures (Llama, Mistral, Qwen, Gemma) or `base_model: encoder_bert` for BERT-family encoders. Configuration lives entirely in the Truss `config.yaml`; the `llm_config` Management API block applies only to v2. For MoE text generation on v2, see [BIS-LLM](/engines/bis-llm/overview).

## Architectures

BEI runs causal embedding architectures (Llama, Mistral, Qwen, Gemma) with `FP8` and `FP4` quantization for maximum throughput. For bidirectional encoders like BERT, RoBERTa, Jina, Nomic, and ModernBERT, BEI ships a more specialized variant called BEI-Bert. BEI-Bert runs at `FP16` or `BF16` and is optimized for cold-start sensitive workloads and models under 4B parameters.

<CardGroup>
  <Card title="BEI" href="#embeddings" icon="brain-circuit">
    Causal embeddings with `FP8`/`FP4` quantization. Up to 1,400 embeddings per second on H100, 121K tokens/s on B200.
  </Card>

  <Card title="BEI-Bert" href="/engines/bei/bei-bert" icon="microchip">
    Bidirectional BERT-family encoders at `FP16` or `BF16`. Tuned for fast cold-start on models under 4B parameters.
  </Card>
</CardGroup>

## Workflows

BEI handles three common workflows: embeddings (`/v1/embeddings`), reranking and classification (`/rerank` and `/predict`), and named entity recognition (`/predict_tokens`, BEI-Bert only). All three share the same `trt_llm` configuration block; the route and `base_model` change per workflow.

### Embeddings

Causal embedders (Llama, Mistral, Qwen, Gemma) deploy on BEI with `base_model: encoder` and pull weights from Hugging Face by default.

```yaml theme={"system"}
trt_llm:
  inference_stack: v1
  build:
    base_model: encoder
    checkpoint_repository:
      source: HF
      repo: "BAAI/bge-large-en-v1.5"
    quantization_type: fp8
  runtime:
    webserver_default_route: /v1/embeddings
```

For embedding models, BEI reads pooling strategy from the Hugging Face repo at build time using `modules.json` and `1_Pooling/config.json`. You do not set pooling in `config.yaml`. See [Pooling layer support](/engines/bei/bei-reference#pooling-layer-support) for the full matrix including SPLADE on BEI-Bert.

### Reranking and classification

Reranking and classification models route to `/rerank` or `/predict` and use the same `trt_llm` block.

```yaml theme={"system"}
trt_llm:
  inference_stack: v1
  build:
    base_model: encoder
    checkpoint_repository:
      source: HF
      repo: "BAAI/bge-reranker-v2-m3"
    max_num_tokens: 16384
  runtime:
    webserver_default_route: /rerank
```

POST query-document pairs to `/rerank`:

```json theme={"system"}
{
  "query": "What is the best way to invest money?",
  "texts": [
    "Index funds offer diversified market exposure.",
    "Day trading requires active monitoring."
  ]
}
```

The response is `[{"index": 0, "score": 0.92}, {"index": 1, "score": 0.14}]`, ordered by the input `texts`. Sort by `score` descending to rerank. Some rerankers (such as `michaelfeil/Qwen3-Reranker-8B-seq`) expect chat-style prompt templates and need `webserver_default_route: /predict` instead; use the [Performance Client](/inference/performance-client) so it applies the right template and autoscaling counts load correctly.

For classification models, set `base_model: encoder_bert` and `webserver_default_route: /predict`. The classifier head needs an `id2label` dictionary in the Hugging Face config; the build fails with a clear error if it is missing.

### Named entity recognition

Token-level entity classification deploys on BEI-Bert only and routes to `/predict_tokens`. The full request/response format and Python example live on [Named entity recognition](/engines/bei/ner).

## OpenAI compatibility

BEI deployments expose `/v1/embeddings` and work with the standard OpenAI client:

```python theme={"system"}
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ['BASETEN_API_KEY'],
    base_url="https://model-xxxxxx.api.baseten.co/environments/production/sync/v1"
)

embedding = client.embeddings.create(
    input=["Baseten Embeddings are fast.", "Embed this sentence!"],
    model="not-required"
)
```

For maximum throughput on batched workloads, use the [Baseten Performance Client](/inference/performance-client) instead. It manages concurrency and batching for you.

## Related

* [BEI configuration reference](/engines/bei/bei-reference): Full `trt_llm` schema, pooling matrix, hardware support, and throughput benchmarks.
* [BEI-Bert](/engines/bei/bei-bert): BERT-specific configuration, model recommendations, and cold-start guidance.
* [Named entity recognition](/engines/bei/ner): `/predict_tokens` request and response format.
* [Embedding examples](/examples/bei): Concrete deployment examples.
* [Performance Client](/inference/performance-client): High-throughput batch inference for embeddings and reranking.
