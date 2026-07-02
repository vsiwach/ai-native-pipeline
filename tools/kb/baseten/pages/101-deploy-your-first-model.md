# Deploy your first model
Source: https://docs.baseten.co/examples/deploy-your-first-model

Deploy an open-source LLM to Baseten with just a config file and get an OpenAI-compatible API endpoint.

Deploying a model to Baseten turns a Hugging Face model into a production-ready API endpoint. You write a `config.yaml` that specifies the model, the hardware, and the engine, then `uvx truss push` builds a TensorRT-optimized container and deploys it. No Python code, no Dockerfile, no container management.

This guide walks through deploying [Qwen 2.5 3B Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct), a small but capable LLM, from a config file to a production API. You'll set up Truss, write a config, deploy to Baseten, and call the model's OpenAI-compatible endpoint.

## Install and sign in

Before you begin, [sign up](https://app.baseten.co/signup) or [sign in](https://app.baseten.co/login) to Baseten, then install [uv](https://docs.astral.sh/uv/), a fast Python package manager.

Install the Truss CLI and connect it to your Baseten account. Browser login opens a tab to approve this device, so there's no API key to copy and paste.

<Columns>
  <Column>
    **Install Truss**

    ```sh theme={"system"}
    uv tool install truss
    ```
  </Column>

  <Column>
    **Sign in**

    ```sh theme={"system"}
    truss login --browser
    ```
  </Column>
</Columns>

<Tip>
  Prefer not to install? Run `uvx truss login --browser` to use the same flow without a permanent install, and use `uvx truss …` for the rest of this guide.
</Tip>

***

## Create a Truss project

Create a directory for your project:

```sh theme={"system"}
mkdir qwen-2.5-3b && cd qwen-2.5-3b
```

TRT-LLM engine deployments only need a `config.yaml`. No custom Python code is required, and the `model/` directory (used for [custom preprocessing or postprocessing](/examples/customize-a-model)) isn't needed here.

***

## Write the config

Create a `config.yaml` with:

```yaml config.yaml theme={"system"}
model_metadata:
  tags:
    - openai-compatible
model_name: Qwen-2.5-3B
resources:
  accelerator: L4
  use_gpu: true
trt_llm:
  build:
    base_model: decoder
    checkpoint_repository:
      source: HF
      repo: "Qwen/Qwen2.5-3B-Instruct"
    max_seq_len: 8192
    quantization_type: fp8
    tensor_parallel_count: 1
    num_builder_gpus: 2
```

That's the entire deployment specification.

* `model_name` identifies the model in your Baseten dashboard.
* `resources` selects an L4 GPU (24 GB VRAM), which is plenty for a 3B parameter model.
* `trt_llm` tells Baseten to use [Engine-Builder-LLM](/engines/engine-builder-llm/overview), which compiles the model with TensorRT-LLM for optimized inference.
* `checkpoint_repository` points to the model weights on Hugging Face. Qwen 2.5 3B Instruct is ungated, so no access token is needed.
* `quantization_type: fp8` compresses weights to 8-bit floating point, cutting memory usage roughly in half with negligible quality loss.
* `max_seq_len: 8192` sets the maximum context length for requests.
* `num_builder_gpus: 2` uses two GPUs during the build phase. FP8 quantization requires more GPU memory at build time than at inference time, so a single L4 runs out of memory during compilation without this setting.

***

## Deploy

Push the model to Baseten:

<Note>
  Engine-based deployments (TRT-LLM) use published deployments by default. The `--watch` flag, which creates a development deployment with live reload, is not supported for TRT-LLM models. For custom Python models, see [Customize a model](/examples/customize-a-model) where `--watch` enables a faster development loop.
</Note>

```sh theme={"system"}
truss push
```

You should see:

```output theme={"system"}
✨ Model Qwen 2.5 3B was successfully pushed ✨

   Model ID:      abc1d2ef
   Deployment ID: xyz123
   Endpoint:      model-abc1d2ef.api.baseten.co
   Logs:          https://app.baseten.co/models/abc1d2ef/logs/xyz123
```

`truss push` prints your model ID (for example, `abc1d2ef`). You'll need it to call the model's API. You can also find it in your [Baseten dashboard](https://app.baseten.co/models/).

Baseten downloads the model weights from Hugging Face, compiles them with TensorRT-LLM, and deploys the resulting container to an L4 GPU. This build step takes roughly 10-20 minutes for the first deploy. You can watch progress in the logs linked above.

***

## Call the model

Engine-based deployments serve an OpenAI-compatible API. Once the deployment shows "Active" in the dashboard, call it using the OpenAI SDK or cURL. Replace `{model_id}` with your model ID from the deployment output.

<Tabs>
  <Tab title="Python">
    Install the OpenAI SDK if you don't have it:

    ```sh theme={"system"}
    uv pip install openai
    ```

    Create a chat completion:

    ```python theme={"system"}
    import os
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["BASETEN_API_KEY"],
        base_url="https://model-{model_id}.api.baseten.co/environments/production/sync/v1",
    )

    response = client.chat.completions.create(
        model="Qwen-2.5-3B",
        messages=[
            {"role": "user", "content": "What is machine learning?"}
        ],
    )

    print(response.choices[0].message.content)
    ```
  </Tab>

  <Tab title="cURL">
    ```sh theme={"system"}
    curl -s https://model-{model_id}.api.baseten.co/environments/production/sync/v1/chat/completions \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -d '{
        "model": "Qwen-2.5-3B",
        "messages": [
          {"role": "user", "content": "What is machine learning?"}
        ]
      }'
    ```
  </Tab>
</Tabs>

You should see a response like:

```output theme={"system"}
Machine learning is a branch of artificial intelligence where systems learn
patterns from data to make predictions or decisions without being explicitly
programmed for each task...
```

Any code that works with the OpenAI SDK works with your deployment. Just point the `base_url` at your model's endpoint.

***

## Next steps

<CardGroup>
  <Card title="Engine configuration" icon="gear" href="/engines/engine-builder-llm/engine-builder-config">
    Tune max sequence length, batch size, quantization, and runtime settings.
  </Card>

  <Card title="Customize a model" icon="code" href="/examples/customize-a-model">
    Add custom Python code when you need preprocessing, postprocessing, or unsupported model architectures.
  </Card>

  <Card title="Autoscaling" icon="arrows-up-down" href="/deployment/autoscaling/overview">
    Configure replicas, concurrency targets, and scale-to-zero for production traffic.
  </Card>
</CardGroup>
