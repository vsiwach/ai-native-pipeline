# Qwen3 Embedding
Source: https://docs.baseten.co/examples/models/embedding/qwen3-embedding

Alibaba's Qwen3 Embedding is an 8B text embedding model that maps text into dense vectors for semantic search, retrieval-augmented generation, clustering, and classification.

<div>
  <a href="/examples/models/capabilities/embedding">Embeddings</a>
</div>

## Setup

To get started, sign into Baseten with Truss and then install the OpenAI SDK.

<Columns>
  <Column>
    **Sign in to Baseten**

    ```sh theme={"system"}
    uvx truss login --browser
    ```
  </Column>

  <Column>
    **Install the OpenAI SDK**

    ```sh theme={"system"}
    uv pip install openai
    ```
  </Column>
</Columns>

[Qwen/Qwen3-Embedding-8B](https://huggingface.co/Qwen/Qwen3-Embedding-8B) is an 8B-parameter dense model.

<CardGroup>
  <Card title="Hardware" icon="microchip">H100</Card>
  <Card title="Engine" icon="server">TRT-LLM</Card>
</CardGroup>

## Write the config

Create and move into the project directory:

```sh theme={"system"}
mkdir qwen3-embedding-8b && cd qwen3-embedding-8b
```

Then create a file named `config.yaml` and paste the following:

```yaml config.yaml theme={"system"}
model_metadata:
  example_model_input:
    input:
      - Baseten is a fast inference provider
      - Embeddings let you do semantic search.
    model: qwen3-embedding-8b
model_name: "model:qwen3-embedding-8b preset:throughput"
python_version: py39
resources:
  accelerator: H100
  cpu: '1'
  memory: 10Gi
  use_gpu: true
trt_llm:
  build:
    base_model: encoder
    checkpoint_repository:
      repo: michaelfeil/Qwen3-Embedding-8B-auto
      revision: main
      source: HF
    max_num_tokens: 40960
    num_builder_gpus: 1
    quantization_type: fp8
  runtime:
    webserver_default_route: /v1/embeddings
```

## Key parameters

[Baseten Embeddings Inference](/engines/bei/overview) (BEI) reads these fields from the `trt_llm` block. Each one shapes how the engine is built and served:

| Parameter       | Value     |
| --------------- | --------- |
| Quantization    | `fp8`     |
| Base model type | `encoder` |

## Deploy

Push the config to Baseten:

```sh theme={"system"}
uvx truss push
```

You should see output similar to:

```output theme={"system"}
✨ Model qwen3-embedding-8b was successfully pushed ✨

   Model ID:      abc1d2ef
   Deployment ID: xyz123
   Endpoint:      model-abc1d2ef.api.baseten.co
   Logs:          https://app.baseten.co/models/abc1d2ef/logs/xyz123
```

Your **model ID** is printed in the `truss push` output (`abcd1234` in the example). Use it wherever you see `{model_id}` in the next section.

## Call the model

Your deployment serves an OpenAI-compatible embeddings API at `/v1/embeddings`. Replace `{model_id}` with your model ID and make sure `BASETEN_API_KEY` is set.

Now call your deployment to generate embeddings:

<Tabs>
  <Tab title="Python">
    ```python main.py theme={"system"}
    import os
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["BASETEN_API_KEY"],
        base_url="https://model-{model_id}.api.baseten.co/environments/production/sync/v1",
    )

    response = client.embeddings.create(
        model="qwen3-embedding-8b",
        input=[
            "Baseten is a fast inference provider.",
            "Embeddings power semantic search and RAG.",
        ],
    )

    for item in response.data:
        print(len(item.embedding), item.embedding[:4])
    ```
  </Tab>

  <Tab title="cURL">
    ```sh theme={"system"}
    curl -s https://model-{model_id}.api.baseten.co/environments/production/sync/v1/embeddings \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -d '{
        "model": "qwen3-embedding-8b",
        "input": [
          "Baseten is a fast inference provider.",
          "Embeddings power semantic search and RAG."
        ]
      }'
    ```
  </Tab>
</Tabs>

For higher throughput, use the [Baseten Performance Client](https://www.baseten.co/blog/your-client-code-matters-10x-higher-embedding-throughput-with-python-and-rust/), which batches and pipelines requests automatically.
