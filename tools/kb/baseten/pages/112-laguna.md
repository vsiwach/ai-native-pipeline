# Laguna
Source: https://docs.baseten.co/examples/models/llm/laguna

Poolside's Laguna M.1 is a Mixture-of-Experts reasoning model tuned for agentic coding and extended reasoning, served from an FP8 checkpoint.

<div>
  <a href="/examples/models/capabilities/agentic">Agentic</a>
  <a href="/examples/models/capabilities/reasoning">Reasoning</a>
  <a href="/examples/models/capabilities/tool-calling">Tool calling</a>
  <a href="/examples/models/capabilities/long-context">Long context</a>
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

[poolside/Laguna-M.1-FP8](https://huggingface.co/poolside/Laguna-M.1-FP8) is a MoE model with up to 256K context.

This preset serves Laguna M.1 on H100:4 with FP8 weights, optimized for low time-to-first-token on interactive reasoning and coding workloads.

<CardGroup>
  <Card title="Hardware" icon="microchip">H100 × 4</Card>
  <Card title="Engine" icon="server">vLLM 0.21.0</Card>
  <Card title="Context" icon="ruler-horizontal">256K</Card>
  <Card title="Concurrency" icon="layer-group">64</Card>
</CardGroup>

## Write the config

Create and move into the project directory:

```sh theme={"system"}
mkdir laguna-m.1-latency && cd laguna-m.1-latency
```

Then create a file named `config.yaml` and paste the following:

```yaml config.yaml theme={"system"}
model_name: "model:laguna-m.1 preset:latency"

model_metadata:
  description: >-
    Laguna M.1 FP8 MoE reasoning model from Poolside, served with vLLM (H100 TP=4),
    OpenAI-compatible chat with tool calling and extended reasoning support.
    Latency-optimized: low max-num-seqs to minimize head-of-line blocking from long thinking traces.
  repo_id: poolside/Laguna-M.1-FP8
  trust_remote_code: true
  tags:
    - openai-compatible
    - vllm
    - moe
    - reasoning
    - agentic-coding
    - fp8
  example_model_input:
    model: poolside/laguna-m.1
    messages:
      - role: user
        content: "Write a Python retry wrapper with exponential backoff."
    stream: true
    temperature: 1.0
    top_k: 20

# ---------------------------------------------------------------------------
# Base image — vLLM with Laguna support (requires vLLM >= 0.21.0)
# ---------------------------------------------------------------------------
base_image:
  image: vllm/vllm-openai:v0.21.0
  python_executable_path: /usr/bin/python3

# ---------------------------------------------------------------------------
# Weights — FP8 quantized checkpoint (~225 GB, fits in 4× H100 / 320 GB)
# Quantization is detected automatically from the checkpoint's
# quantization_config — no extra vLLM flags needed.
# ---------------------------------------------------------------------------
weights:
  - source: "hf://poolside/Laguna-M.1-FP8"
    mount_location: "/models/laguna-m1"

environment_variables:
  VLLM_LOGGING_LEVEL: WARNING
  VLLM_ENGINE_READY_TIMEOUT_S: "3600"

# ---------------------------------------------------------------------------
# Docker server — vLLM OpenAI-compatible endpoint
# ---------------------------------------------------------------------------
docker_server:
  start_command: >
    vllm serve /models/laguna-m1
    --served-model-name poolside/laguna-m.1
    --host 0.0.0.0
    --port 8000
    --tool-call-parser poolside_v1
    --reasoning-parser poolside_v1
    --enable-auto-tool-choice
    --default-chat-template-kwargs '{"enable_thinking": true}'
    --tensor-parallel-size 4
    --max-model-len 262144
    --max-num-seqs 64
    --gpu-memory-utilization 0.95
    --trust-remote-code
  readiness_endpoint: /health
  liveness_endpoint: /health
  predict_endpoint: /v1/chat/completions
  server_port: 8000

# ---------------------------------------------------------------------------
# Resources
# FP8 ~225 GB → 4× H100 (320 GB total VRAM) with comfortable headroom
# ---------------------------------------------------------------------------
resources:
  accelerator: H100:4
  cpu: "8"
  memory: 32Gi
  use_gpu: true

# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
runtime:
  predict_concurrency: 64
  health_checks:
    restart_check_delay_seconds: 1800
    restart_threshold_seconds: 600
    stop_traffic_threshold_seconds: 180
```

## Flags

The `start_command` passes these flags to the engine. Each one controls a runtime or serving behavior:

| Flag                             | Value                       | What it does                                                                                                      |
| -------------------------------- | --------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `--tool-call-parser`             | `poolside_v1`               | Server-side parser that emits structured `tool_calls` on the response.                                            |
| `--reasoning-parser`             | `poolside_v1`               | Server-side parser that separates reasoning output into `reasoning_content`.                                      |
| `--enable-auto-tool-choice`      | (no value)                  | Let the model choose when to call tools without requiring `tool_choice: "required"`.                              |
| `--default-chat-template-kwargs` | `{"enable_thinking": true}` | Default keyword arguments applied to the chat template, used to set behaviors like enabling reasoning by default. |
| `--tensor-parallel-size`         | `4`                         | Number of GPUs to shard the model across.                                                                         |
| `--max-model-len`                | `262144`                    | Maximum context length (tokens) the server accepts per request.                                                   |
| `--max-num-seqs`                 | `64`                        | Maximum number of concurrent sequences in the batch.                                                              |
| `--gpu-memory-utilization`       | `0.95`                      | Fraction of GPU memory vLLM may use for weights and KV cache.                                                     |
| `--trust-remote-code`            | (no value)                  | Execute model-specific Python from the checkpoint (required for many Qwen, Phi, and custom architectures).        |

## Deploy

Push the config to Baseten:

```sh theme={"system"}
uvx truss push
```

You should see output similar to:

```output theme={"system"}
✨ Model laguna-m.1-latency was successfully pushed ✨

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
        model="poolside/laguna-m.1",
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
        "model": "poolside/laguna-m.1",
        "messages": [
          {"role": "user", "content": "What is machine learning?"}
        ]
      }'
    ```
  </Tab>
</Tabs>

The server parses the model's chain of thought into a separate `reasoning_content` field on the response. Read it alongside the final answer:

```python theme={"system"}
response = client.chat.completions.create(
    model="poolside/laguna-m.1",
    messages=[
        {"role": "user", "content": "How many r's in strawberry?"}
    ],
)
print(response.choices[0].message.reasoning_content)  # chain of thought
print(response.choices[0].message.content)            # final answer
```

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
    model="poolside/laguna-m.1",
    messages=[
        {"role": "user", "content": "What's the weather in Paris?"}
    ],
    tools=tools,
)
print(response.choices[0].message.tool_calls)
```
