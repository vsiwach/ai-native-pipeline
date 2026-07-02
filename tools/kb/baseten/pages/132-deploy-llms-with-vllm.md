# Deploy LLMs with vLLM
Source: https://docs.baseten.co/examples/vllm

Run any open-source LLM on vLLM's serving framework.

[vLLM](https://docs.vllm.ai/) supports a wide range of models and performance optimizations. This guide deploys a vLLM model as a custom Docker server on Baseten.

This configuration serves [Qwen 2.5 3B](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct) with vLLM on an L4 GPU. The deployment process is the same for larger models like [GLM-4.7](https://huggingface.co/zai-org/GLM-4.7). Adjust the `resources` and `start_command` to match your model's requirements.

## Set up your environment

This guide uses `uvx` to run [Truss](https://pypi.org/project/truss/) commands without a separate install step. Sign in to Baseten and install the OpenAI SDK. Browser login opens a tab to approve this device, so there's no API key to copy and paste.

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

<Note>
  **Hugging Face access for gated models.** Some models require that you accept terms and conditions on Hugging Face before deployment. To prevent issues:

  1. Accept the license for any gated models you wish to access, like [Gemma 3](https://huggingface.co/google/gemma-3-27b-it).
  2. Create a read-only [user access token](https://huggingface.co/docs/hub/en/security-tokens) from your Hugging Face account.
  3. Add the `hf_access_token` secret [to your Baseten workspace](https://app.baseten.co/settings/secrets).
  4. Reference it from the weight source's `auth` block (below). The secret alone does not authenticate weight mirroring, so without `auth` a gated repo fails to deploy with a `401`.
</Note>

## Configure the model

Create a directory with a `config.yaml` file:

```sh theme={"system"}
mkdir qwen-2-5-3b-vllm
touch qwen-2-5-3b-vllm/config.yaml
```

Copy the following configuration into `config.yaml`:

```yaml config.yaml theme={"system"}
model_metadata:
  example_model_input:
    messages:
      - role: system
        content: "You are a helpful assistant."
      - role: user
        content: "What does Tongyi Qianwen mean?"
    stream: true
    model: Qwen/Qwen2.5-3B-Instruct
    max_tokens: 512
    temperature: 0.6
  tags:
    - openai-compatible
model_name: Qwen 2.5 3B vLLM
base_image:
  image: vllm/vllm-openai:v0.12.0
docker_server:
  start_command: vllm serve /models/qwen --served-model-name Qwen/Qwen2.5-3B-Instruct --host 0.0.0.0 --port 8000 --enable-prefix-caching
  readiness_endpoint: /health
  liveness_endpoint: /health
  predict_endpoint: /v1/chat/completions
  server_port: 8000
weights:
  - source: "hf://Qwen/Qwen2.5-3B-Instruct@aa8e72537993ba99e69dfaafa59ed015b17504d1"
    mount_location: "/models/qwen"
    auth:
      auth_method: CUSTOM_SECRET
      auth_secret_name: "hf_access_token"  # Required for private or gated repos
resources:
  accelerator: L4
  use_gpu: true
runtime:
  predict_concurrency: 256
  health_checks:
    restart_threshold_seconds: 300
    stop_traffic_threshold_seconds: 120
```

The `base_image` specifies the [vLLM Docker image](https://hub.docker.com/r/vllm/vllm-openai/tags). The `weights` block uses the [Baseten Delivery Network](/development/model/bdn) to mirror the model from Hugging Face and mount it at `/models/qwen` before the container starts. vLLM reads weights directly from that path and serves the model with `--served-model-name`, which sets the model identifier for the OpenAI-compatible API. The `health_checks` settings control how Baseten monitors the server after it passes the [startup probe](/development/model/health-checks).

## Deploy the model

Push the model to Baseten to start the deployment:

```sh theme={"system"}
uvx truss push qwen-2-5-3b-vllm
```

You should see output like:

```output theme={"system"}
✨ Model Qwen 2.5 3B vLLM was successfully pushed ✨

   Model ID:      abc1d2ef
   Deployment ID: xyz123
   Endpoint:      model-abc1d2ef.api.baseten.co
   Logs:          https://app.baseten.co/models/abc1d2ef/logs/xyz123
```

Copy the model URL from the output for the next step.

The first deploy can take several minutes while Baseten pulls the vLLM base image. Subsequent scale-ups reuse the cached image and start much faster.

## Call the model

Call the deployed model with the OpenAI client:

```python call_model.py theme={"system"}
import os
from openai import OpenAI

model_url = "https://model-XXXXXXX.api.baseten.co/environments/production/sync/v1"

client = OpenAI(
    base_url=model_url,
    api_key=os.environ.get("BASETEN_API_KEY"),
)

stream = client.chat.completions.create(
    model="Qwen/Qwen2.5-3B-Instruct",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What does Tongyi Qianwen mean?"}
    ],
    stream=True,
)

for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="")
```

Replace the `model_url` with the URL from your deployment output.

## Monitor your deployment

Once the model is serving traffic, open the Metrics tab in the model dashboard to watch how it performs. Baseten detects the vLLM engine and surfaces engine-native graphs such as token throughput, inter-token latency, KV cache usage, and queue depth alongside the standard metrics. See [vLLM and SGLang metrics](/observability/metrics#vllm-and-sglang-metrics).

## Route through an external LLM gateway

To route traffic from a third-party OpenAI-compatible gateway to this deployment, see [External LLM gateways](/inference/calling-your-model#external-llm-gateways). The `model` value the gateway sends must match the `--served-model-name` in the `start_command` above.
