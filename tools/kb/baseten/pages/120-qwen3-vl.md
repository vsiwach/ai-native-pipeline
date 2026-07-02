# Qwen3-VL
Source: https://docs.baseten.co/examples/models/llm/qwen3-vl

Qwen3-VL-32B-Instruct is a 32B-parameter dense vision-language model. This recipe serves the RedHatAI NVFP4 quantization with image input and native tool calling.

<div>
  <a href="/examples/models/capabilities/multimodal-image">Multimodal (image)</a>
  <a href="/examples/models/capabilities/tool-calling">Tool calling</a>
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

[RedHatAI/Qwen3-VL-32B-Instruct-NVFP4](https://huggingface.co/RedHatAI/Qwen3-VL-32B-Instruct-NVFP4) is a 32B-parameter dense model.

This preset serves the RedHatAI NVFP4 quantization of Qwen3-VL-32B-Instruct on a single RTX PRO 6000 Blackwell GPU, optimized for throughput on vision-language workloads.

<CardGroup>
  <Card title="Hardware" icon="microchip">RTX\_PRO\_6000</Card>
  <Card title="Engine" icon="server">vLLM (0.22.0-cu129 build)</Card>
  <Card title="Concurrency" icon="layer-group">8</Card>
</CardGroup>

## Write the config

Create and move into the project directory:

```sh theme={"system"}
mkdir qwen3-vl-32b-throughput && cd qwen3-vl-32b-throughput
```

Then create a file named `config.yaml` and paste the following:

```yaml config.yaml theme={"system"}
model_name: "model:qwen3-vl-32b preset:throughput"
model_metadata:
  description: >-
    Qwen3-VL-32B-Instruct (NVFP4), an OpenAI-compatible multimodal chat model with
    vision served via vLLM.
  repo_id: RedHatAI/Qwen3-VL-32B-Instruct-NVFP4
  example_model_input:
    model: Qwen/Qwen3-VL-32B-Instruct
    messages:
      - role: user
        content:
          - type: text
            text: "Describe this image in one sentence."
          - type: image_url
            image_url:
              url: "https://picsum.photos/id/237/200/300"
    stream: true
    max_tokens: 512
    temperature: 1.0
  tags:
    - openai-compatible
base_image:
  image: vllm/vllm-openai:v0.22.0-cu129
weights:
  - source: "hf://RedHatAI/Qwen3-VL-32B-Instruct-NVFP4@main"
    mount_location: "/app/checkpoint/model"
    auth_secret_name: "hf_access_token"
secrets:
  hf_access_token: null
docker_server:
  start_command: >-
    sh -c "GPU_COUNT=$(nvidia-smi --list-gpus | wc -l) && vllm serve /app/checkpoint/model
    --tensor-parallel-size $GPU_COUNT
    --served-model-name Qwen/Qwen3-VL-32B-Instruct
    --max-num-seqs 16
    --max-model-len auto
    --limit-mm-per-prompt.image 2
    --gpu-memory-utilization 0.9
    --enable-prefix-caching
    --trust-remote-code
    --enable-auto-tool-choice
    --tool-call-parser hermes
    --load-format runai_streamer"
  readiness_endpoint: /health
  liveness_endpoint: /health
  predict_endpoint: /v1/chat/completions
  server_port: 8000
environment_variables:
  VLLM_LOGGING_LEVEL: WARNING
  VLLM_ENGINE_READY_TIMEOUT_S: "3600"
resources:
  accelerator: RTX_PRO_6000
  use_gpu: true
runtime:
  health_checks:
    restart_check_delay_seconds: 1800
    restart_threshold_seconds: 1200
    stop_traffic_threshold_seconds: 120
  predict_concurrency: 8
```

## Flags

The `start_command` passes these flags to the engine. Each one controls a runtime or serving behavior:

| Flag                          | Value            | What it does                                                                                                    |
| ----------------------------- | ---------------- | --------------------------------------------------------------------------------------------------------------- |
| `--tensor-parallel-size`      | `$GPU_COUNT`     | Number of GPUs to shard the model across.                                                                       |
| `--max-num-seqs`              | `16`             | Maximum number of concurrent sequences in the batch.                                                            |
| `--max-model-len`             | `auto`           | Maximum context length (tokens) the server accepts per request.                                                 |
| `--limit-mm-per-prompt.image` | `2`              | Maximum number of image inputs per prompt.                                                                      |
| `--gpu-memory-utilization`    | `0.9`            | Fraction of GPU memory vLLM may use for weights and KV cache.                                                   |
| `--enable-prefix-caching`     | (no value)       | Reuse KV cache across requests that share a prefix.                                                             |
| `--trust-remote-code`         | (no value)       | Execute model-specific Python from the checkpoint (required for many Qwen, Phi, and custom architectures).      |
| `--enable-auto-tool-choice`   | (no value)       | Let the model choose when to call tools without requiring `tool_choice: "required"`.                            |
| `--tool-call-parser`          | `hermes`         | Server-side parser that emits structured `tool_calls` on the response. **hermes:** Hermes-style function calls. |
| `--load-format`               | `runai_streamer` | Weight loading backend. **runai\_streamer:** Stream weights from object storage without materializing to disk.  |

## Deploy

Push the config to Baseten:

```sh theme={"system"}
uvx truss push
```

You should see output similar to:

```output theme={"system"}
✨ Model qwen3-vl-32b-throughput was successfully pushed ✨

   Model ID:      abc1d2ef
   Deployment ID: xyz123
   Endpoint:      model-abc1d2ef.api.baseten.co
   Logs:          https://app.baseten.co/models/abc1d2ef/logs/xyz123
```

Your **model ID** is printed in the `truss push` output (`abcd1234` in the example). Use it wherever you see `{model_id}` in the next section.

## Call the model

Your deployment serves an OpenAI-compatible API. Replace `{model_id}` with your model ID and make sure `BASETEN_API_KEY` is set.

Now call your deployment to run inference:

<Tabs>
  <Tab title="Python">
    ```python main.py theme={"system"}
    import os
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["BASETEN_API_KEY"],
        base_url="https://model-{model_id}.api.baseten.co/environments/production/sync/v1",
    )

    response = client.chat.completions.create(
        model="Qwen/Qwen3-VL-32B-Instruct",
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
        "model": "Qwen/Qwen3-VL-32B-Instruct",
        "messages": [
          {"role": "user", "content": "What is machine learning?"}
        ]
      }'
    ```
  </Tab>
</Tabs>

To let the model call tools, pass a `tools` array. The server returns structured `tool_calls` on the response:

```python theme={"system"}
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "parameters": {
            "type": "object",
            "properties": {"location": {"type": "string"}},
            "required": ["location"],
        },
    },
}]

response = client.chat.completions.create(
    model="Qwen/Qwen3-VL-32B-Instruct",
    messages=[
        {"role": "user", "content": "What's the weather in Paris?"}
    ],
    tools=tools,
)
print(response.choices[0].message.tool_calls)
```
