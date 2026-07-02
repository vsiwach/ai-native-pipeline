# Build your model
Source: https://docs.baseten.co/development/model/build-your-first-model

Deploy a model to Baseten with just a config file. Pick an open-source model from Hugging Face, choose a GPU, and get an endpoint in minutes.

Baseten deploys models from a single `config.yaml` file. You point to a model on Hugging Face, choose a GPU, and Baseten builds a TensorRT-optimized container with an OpenAI-compatible API. No Python code, no Dockerfile, no container management.

This tutorial deploys [Qwen 2.5 3B Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) to a production-ready endpoint on an L4 GPU.

## Install and sign in

Before you begin, [sign up](https://app.baseten.co/signup) or [sign in](https://app.baseten.co/login) to Baseten, then install [uv](https://docs.astral.sh/uv/), a fast Python package manager.

Install the Truss CLI and connect it to your Baseten account. Browser login opens a tab to approve this device, so there's no API key to copy and paste.

<Columns>
  <Column>
    **Install Truss**

    ```bash Terminal theme={"system"}
    uv tool install truss
    ```
  </Column>

  <Column>
    **Sign in**

    ```bash Terminal theme={"system"}
    truss login --browser
    ```
  </Column>
</Columns>

<Tip>
  Prefer not to install? Run `uvx truss login --browser` to use the same flow without a permanent install, and use `uvx truss …` for the rest of this guide.
</Tip>

## Create the config

Create a project directory with a `config.yaml`:

```bash Terminal theme={"system"}
mkdir qwen-2.5-3b && cd qwen-2.5-3b
```

Create a `config.yaml` file with the following contents:

```yaml config.yaml theme={"system"}
model_name: Qwen-2.5-3B
resources:
  accelerator: L4
model_metadata:
  tags:
    - openai-compatible
trt_llm:
  build:
    base_model: decoder
    checkpoint_repository:
      source: HF
      repo: "Qwen/Qwen2.5-3B-Instruct"
    max_seq_len: 8192
    quantization_type: fp8
    tensor_parallel_count: 1
    num_builder_gpus: 1
```

What each field does:

* `resources.accelerator: L4` runs inference on a single L4 (24 GB VRAM).
* `trt_llm` switches on [Engine-Builder-LLM](/engines/engine-builder-llm/overview), which compiles the model with TensorRT-LLM.
* `checkpoint_repository` points to weights on Hugging Face. Qwen 2.5 3B Instruct is ungated, so no token is needed.
* `quantization_type: fp8` halves weight memory by quantizing to 8-bit floats.
* `num_builder_gpus: 1` sets the GPU count for the engine-build job. Without it, the CLI warns that FP8 builds can OOM at build time.

## Deploy

Push to Baseten:

```bash Terminal theme={"system"}
truss push
```

You should see:

```output theme={"system"}
✨ Model Qwen-2.5-3B was successfully pushed ✨

   Model ID:      abc1d2ef
   Deployment ID: xyz123
   Endpoint:      model-abc1d2ef.api.baseten.co
   Logs:          https://app.baseten.co/models/abc1d2ef/logs/xyz123
```

The CLI prints your **Model ID** (for example, `abc1d2ef`). You'll need it to call the model's API. You can also find it in your [Baseten dashboard](https://app.baseten.co/models/).

Baseten now downloads the model weights, compiles them with TensorRT-LLM, and deploys the resulting container to an L4 GPU. You can watch progress in the logs linked above. When the deployment status shows "Active" in the dashboard, it's ready for requests.

## Call your model

Engine-based deployments serve an OpenAI-compatible API, so any code that works with the OpenAI SDK works with your model. Replace `{model_id}` with your model ID from the deployment output.

<Tabs>
  <Tab title="Python">
    Install the OpenAI SDK if you don't have it:

    ```bash Terminal theme={"system"}
    uv pip install openai
    ```

    Create a chat completion:

    ```python call_model.py theme={"system"}
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
    ```bash Request theme={"system"}
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

## What just happened

From one config file, Baseten:

1. Downloaded the Qwen 2.5 3B Instruct weights from Hugging Face.
2. Compiled them with TensorRT-LLM and FP8 quantization.
3. Packaged the engine into a container on an L4 GPU.
4. Exposed an OpenAI-compatible API at the model's URL.

No `model.py`, no Dockerfile, no inference server configuration. The same pattern works for most popular open-source LLMs, including Llama, Qwen, Mistral, Gemma, and Phi.

## Next steps

<CardGroup>
  <Card title="Engine configuration" icon="gear" href="/engines/engine-builder-llm/engine-builder-config">
    Tune max sequence length, batch size, quantization, and runtime settings for your deployment.
  </Card>

  <Card title="Custom model code" icon="code" href="/development/model/model-class">
    Add custom Python when you need preprocessing, postprocessing, or unsupported model architectures.
  </Card>

  <Card title="Autoscaling" icon="arrows-up-down" href="/deployment/autoscaling/overview">
    Configure replicas, concurrency targets, and scale-to-zero for production traffic.
  </Card>

  <Card title="Promote to production" icon="rocket" href="/deployment/environments">
    Move from development to production with `truss push --promote`.
  </Card>
</CardGroup>
