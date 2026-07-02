# Deploy with optimized inference engines
Source: https://docs.baseten.co/training/deploy-with-engine-builder

Deploy model checkpoints from Baseten Training directly to an inference engine without downloading or re-uploading weights.

When a [Baseten Training](/training/overview) job completes, Baseten automatically saves your checkpoints to Baseten storage. You can deploy any of them to an inference engine without downloading or re-uploading anything.

[Engine-Builder-LLM](/engines/engine-builder-llm/overview), [BEI](/engines/bei/overview), and [BIS-LLM](/engines/bis-llm/overview) all support this workflow.

<Note>
  For deploying weights from external cloud storage (GCS, S3, Azure), see [Deploy from cloud storage](/engines/performance-concepts/cloud-storage-deployment).
</Note>

## Checkpoint reference

The `repo` and `revision` fields in `checkpoint_repository` specify which training project and checkpoint to deploy.

* `repo`: Your Baseten Training project name.
* `revision`: Which job and checkpoint to target. The following formats are supported:

| `revision` value             | Deploys                                                                          |
| ---------------------------- | -------------------------------------------------------------------------------- |
| `<job_id>/<checkpoint_name>` | A specific checkpoint from a specific job (for example, `abc123/checkpoint-100`) |
| `<job_id>`                   | The latest checkpoint from a specific job                                        |
| `latest` or omitted          | The latest checkpoint from the latest job                                        |

To look up checkpoint names for a job, run:

```sh theme={"system"}
truss train get_checkpoint_urls --job-id=YOUR_TRAINING_JOB_ID
```

## LLM deployment

Use [Engine-Builder-LLM](/engines/engine-builder-llm/overview) or [BIS-LLM](/engines/bis-llm/overview) to deploy a fine-tuned language model. Set `base_model` to `decoder`:

```yaml config.yaml theme={"system"}
model_name: My Fine-Tuned LLM
resources:
  accelerator: H100
  use_gpu: true
trt_llm:
  build:
    base_model: decoder
    checkpoint_repository:
      source: BASETEN_TRAINING
      repo: YOUR_TRAINING_PROJECT_NAME
      revision: YOUR_TRAINING_JOB_ID/checkpoint-100
```

Once deployed, call the model using the OpenAI-compatible chat completions endpoint:

```sh theme={"system"}
curl -X POST https://model-YOUR_MODEL_ID.api.baseten.co/environments/production/sync/v1/chat/completions \
  -H "Authorization: Bearer $BASETEN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "1", "messages": [{"role": "user", "content": "Hello"}]}'
```

See [Call your model](/inference/calling-your-model) for full inference options including streaming and the OpenAI SDK.

## Embeddings deployment

Use [BEI](/engines/bei/overview) to deploy a fine-tuned embedding or reranker model. Use `encoder_bert` for BERT-based models (sentence-transformers, rerankers, classifiers) or `encoder` for causal embedding models:

```yaml config.yaml theme={"system"}
model_name: My Fine-Tuned Embeddings
resources:
  accelerator: A10G
  use_gpu: true
trt_llm:
  build:
    base_model: encoder_bert
    checkpoint_repository:
      source: BASETEN_TRAINING
      repo: YOUR_TRAINING_PROJECT_NAME
      revision: YOUR_TRAINING_JOB_ID/checkpoint-100
    max_num_tokens: 16384
  runtime:
    webserver_default_route: /v1/embeddings
```

Encoder models have specific requirements:

* **No tensor parallelism**: Omit `tensor_parallel_count` or set it to `1`.
* **Fast tokenizer required**: Your checkpoint must include a `tokenizer.json` file. Models using only the legacy `vocab.txt` format aren't supported.
* **Embedding model files**: For sentence-transformer models, include `modules.json` and `1_Pooling/config.json` in your checkpoint.

The `webserver_default_route` field sets the inference endpoint path:

* `/v1/embeddings`: For embedding models.
* `/rerank`: For rerankers.
* `/predict`: For classifiers.
* `/predict_tokens`: For token-level prediction.

Once deployed, call the model using the embeddings endpoint:

```sh theme={"system"}
curl -X POST https://model-YOUR_MODEL_ID.api.baseten.co/environments/production/sync/v1/embeddings \
  -H "Authorization: Bearer $BASETEN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "1", "input": "Your text here"}'
```

See [Call your model](/inference/calling-your-model) for full inference options.

## Related

* [Engine-Builder-LLM configuration](/engines/engine-builder-llm/engine-builder-config): Complete build and runtime options for LLMs.
* [BEI reference configuration](/engines/bei/bei-reference): Complete configuration for encoder models.
* [Deploy from cloud storage](/engines/performance-concepts/cloud-storage-deployment): GCS, S3, and Azure deployment using `checkpoint_repository`.
* [Baseten Training overview](/training/overview): Training jobs, checkpoints, and the full training workflow.
* [Secrets management](/development/model/secrets): Configure credentials for private storage.
