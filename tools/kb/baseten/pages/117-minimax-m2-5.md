# MiniMax M2.5
Source: https://docs.baseten.co/examples/models/llm/minimax-m2.5

Large MoE model with native reasoning and tool calling. Uses the MiniMax-specific append-think reasoning format.

<div>
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

[MiniMaxAI/MiniMax-M2.5](https://huggingface.co/MiniMaxAI/MiniMax-M2.5) is a 229B-parameter MoE model with up to 200K context.

This preset serves MiniMax M2.5 on H100:4 with expert-parallel sharding and Runai Streamer weight loading, optimized for maximum batch throughput.

<CardGroup>
  <Card title="Hardware" icon="microchip">H100 × 4</Card>
  <Card title="Engine" icon="server">vLLM (0.22.0-cu129 build)</Card>
  <Card title="Context" icon="ruler-horizontal">200K</Card>
  <Card title="Concurrency" icon="layer-group">64</Card>
</CardGroup>

## Write the config

Create and move into the project directory:

```sh theme={"system"}
mkdir minimax-m2.5-throughput && cd minimax-m2.5-throughput
```

Then create a file named `config.yaml` and paste the following:

```yaml config.yaml theme={"system"}
model_name: "model:minimax-m2.5 preset:throughput"
model_metadata:
  description: >-
    MiniMax-M2.5 Mixture-of-Experts (Run:AI streamer loading), throughput on H100 × 4 with MiniMax parsers.
  repo_id: MiniMaxAI/MiniMax-M2.5
  example_model_input:
    messages:
      - role: system
        content: "You are a helpful assistant."
      - role: user
        content: "What is the meaning of life?"
    stream: true
    model: MiniMaxAI/MiniMax-M2.5
    max_tokens: 32768
    temperature: 0.7
  tags:
    - openai-compatible
base_image:
  image: vllm/vllm-openai:v0.22.0-cu129
weights:
  - source: "hf://MiniMaxAI/MiniMax-M2.5@main"
    mount_location: "/app/checkpoint/model"
    auth_secret_name: "hf_access_token"
    ignore_patterns:
      - "*.md"
      - "*.txt"
secrets:
  hf_access_token: null
environment_variables:
  VLLM_LOGGING_LEVEL: WARNING
  VLLM_ENGINE_READY_TIMEOUT_S: "3600"
docker_server:
  start_command: >-
    sh -c "GPU_COUNT=$(nvidia-smi --list-gpus | wc -l) && SAFETENSORS_FAST_GPU=1 vllm serve /app/checkpoint/model
    --host 0.0.0.0
    --port 8000
    --served-model-name MiniMaxAI/MiniMax-M2.5
    --tensor-parallel-size $GPU_COUNT
    --enable-expert-parallel
    --trust-remote-code
    --load-format runai_streamer
    --disable-log-stats
    --max-num-seqs 64
    --max-num-batched-tokens 8192
    --tool-call-parser minimax_m2
    --reasoning-parser minimax_m2_append_think
    --enable-auto-tool-choice
    --enable-prefix-caching"
  readiness_endpoint: /health
  liveness_endpoint: /health
  predict_endpoint: /v1/chat/completions
  server_port: 8000
resources:
  accelerator: H100:4
  use_gpu: true
runtime:
  predict_concurrency: 64
  health_checks:
    restart_check_delay_seconds: 1800
    restart_threshold_seconds: 1200
    stop_traffic_threshold_seconds: 120
```

## Flags

The `start_command` passes these flags to the engine. Each one controls a runtime or serving behavior:

| Flag                        | Value                     | What it does                                                                                                                                 |
| --------------------------- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `--tensor-parallel-size`    | `$GPU_COUNT`              | Number of GPUs to shard the model across.                                                                                                    |
| `--enable-expert-parallel`  | (no value)                | Shard MoE expert weights across tensor-parallel ranks instead of replicating them, reducing per-GPU memory for large MoE models.             |
| `--trust-remote-code`       | (no value)                | Execute model-specific Python from the checkpoint (required for many Qwen, Phi, and custom architectures).                                   |
| `--load-format`             | `runai_streamer`          | Weight loading backend. **runai\_streamer:** Stream weights from object storage without materializing to disk.                               |
| `--disable-log-stats`       | (no value)                | Suppress periodic engine stats logging.                                                                                                      |
| `--max-num-seqs`            | `64`                      | Maximum number of concurrent sequences in the batch.                                                                                         |
| `--max-num-batched-tokens`  | `8192`                    | Maximum total tokens processed per scheduler step.                                                                                           |
| `--tool-call-parser`        | `minimax_m2`              | Server-side parser that emits structured `tool_calls` on the response. **minimax\_m2:** MiniMax M2 tool format.                              |
| `--reasoning-parser`        | `minimax_m2_append_think` | Server-side parser that separates reasoning output into `reasoning_content`. **minimax\_m2\_append\_think:** MiniMax M2 append-think format. |
| `--enable-auto-tool-choice` | (no value)                | Let the model choose when to call tools without requiring `tool_choice: "required"`.                                                         |
| `--enable-prefix-caching`   | (no value)                | Reuse KV cache across requests that share a prefix.                                                                                          |

## Deploy

Push the config to Baseten:

```sh theme={"system"}
uvx truss push
```

You should see output similar to:

```output theme={"system"}
✨ Model minimax-m2.5-throughput was successfully pushed ✨

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
        model="MiniMaxAI/MiniMax-M2.5",
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
        "model": "MiniMaxAI/MiniMax-M2.5",
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
    model="MiniMaxAI/MiniMax-M2.5",
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
    model="MiniMaxAI/MiniMax-M2.5",
    messages=[
        {"role": "user", "content": "What's the weather in Paris?"}
    ],
    tools=tools,
)
print(response.choices[0].message.tool_calls)
```
