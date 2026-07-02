# Llama 4
Source: https://docs.baseten.co/examples/models/llm/llama-4

Meta's Llama 4 Scout is a 17B-active MoE with native multimodal support and a 10M token context window.

<div>
  <a href="/examples/models/capabilities/tool-calling">Tool calling</a>
  <a href="/examples/models/capabilities/long-context">Long context</a>
  <a href="/examples/models/capabilities/multimodal-image">Multimodal (image)</a>
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

[meta-llama/Llama-4-Scout-17B-16E-Instruct](https://huggingface.co/meta-llama/Llama-4-Scout-17B-16E-Instruct) is a 109B-parameter MoE model (17B active per token) with up to 10M context.

This preset serves Llama 4 Scout on H100:4 with a 128K serving context and native multimodal support.

<CardGroup>
  <Card title="Hardware" icon="microchip">H100 × 4</Card>
  <Card title="Engine" icon="server">vLLM (0.22.0-cu129 build)</Card>
  <Card title="Context" icon="ruler-horizontal">128K</Card>
  <Card title="Concurrency" icon="layer-group">256</Card>
</CardGroup>

## Write the config

Create and move into the project directory:

```sh theme={"system"}
mkdir llama-4-scout-latency && cd llama-4-scout-latency
```

Then create a file named `config.yaml` and paste the following:

```yaml config.yaml theme={"system"}
model_name: "model:llama-4-scout preset:latency"
model_metadata:
  description: >-
    Llama 4 Scout 17B multimodal instruct (RedHat FP8-dynamic), long-context with TP=4 FP8 KV,
    OpenAI-compatible chat via vLLM.
  repo_id: RedHatAI/Llama-4-Scout-17B-16E-Instruct-FP8-dynamic
  example_model_input:
    model: llama
    messages:
      - role: user
        content: "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume that each input would have exactly one solution, and you may not use the same element twice. You can return the answer in any order. class Solution: def twoSum(self, nums: List[int], target: int) -> List[int]:"
    stream: true
    max_tokens: 512
    temperature: 0.5
  tags:
    - openai-compatible
base_image:
  image: vllm/vllm-openai:v0.22.0-cu129
weights:
  - source: "hf://RedHatAI/Llama-4-Scout-17B-16E-Instruct-FP8-dynamic@main"
    mount_location: "/app/checkpoint/model"
    auth_secret_name: "hf_access_token"
secrets:
  hf_access_token: null
environment_variables:
  VLLM_LOGGING_LEVEL: WARNING
  VLLM_ENGINE_READY_TIMEOUT_S: "3600"
docker_server:
  start_command: >-
    sh -c "GPU_COUNT=$(nvidia-smi --list-gpus | wc -l) && vllm serve /app/checkpoint/model
    --served-model-name llama
    --host 0.0.0.0
    --port 8000
    --trust-remote-code
    --max-model-len 131072
    --tensor-parallel-size $GPU_COUNT
    --distributed-executor-backend mp
    --gpu-memory-utilization 0.95
    --kv-cache-dtype fp8
    --limit-mm-per-prompt.image 10
    --override-generation-config.attn_temperature_tuning true
    --enable-prefix-caching
    --load-format runai_streamer"
  readiness_endpoint: /health
  liveness_endpoint: /health
  predict_endpoint: /v1/chat/completions
  server_port: 8000
resources:
  accelerator: H100:4
  use_gpu: true
runtime:
  predict_concurrency: 256
  health_checks:
    restart_check_delay_seconds: 1800
    restart_threshold_seconds: 1200
    stop_traffic_threshold_seconds: 120
```

## Flags

The `start_command` passes these flags to the engine. Each one controls a runtime or serving behavior:

| Flag                                                   | Value            | What it does                                                                                                         |
| ------------------------------------------------------ | ---------------- | -------------------------------------------------------------------------------------------------------------------- |
| `--trust-remote-code`                                  | (no value)       | Execute model-specific Python from the checkpoint (required for many Qwen, Phi, and custom architectures).           |
| `--max-model-len`                                      | `131072`         | Maximum context length (tokens) the server accepts per request.                                                      |
| `--tensor-parallel-size`                               | `$GPU_COUNT`     | Number of GPUs to shard the model across.                                                                            |
| `--distributed-executor-backend`                       | `mp`             | How vLLM coordinates tensor-parallel workers across processes. **mp:** Python multiprocessing (single-node default). |
| `--gpu-memory-utilization`                             | `0.95`           | Fraction of GPU memory vLLM may use for weights and KV cache.                                                        |
| `--kv-cache-dtype`                                     | `fp8`            | KV cache numeric precision. **fp8:** \~2× KV cache density with negligible quality impact on most models.            |
| `--limit-mm-per-prompt.image`                          | `10`             | Maximum number of image inputs per prompt.                                                                           |
| `--override-generation-config.attn_temperature_tuning` | `true`           | Sets the `attn_temperature_tuning` field in the model's generation config.                                           |
| `--enable-prefix-caching`                              | (no value)       | Reuse KV cache across requests that share a prefix.                                                                  |
| `--load-format`                                        | `runai_streamer` | Weight loading backend. **runai\_streamer:** Stream weights from object storage without materializing to disk.       |

## Deploy

Push the config to Baseten:

```sh theme={"system"}
uvx truss push
```

You should see output similar to:

```output theme={"system"}
✨ Model llama-4-scout-latency was successfully pushed ✨

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
        model="llama",
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
        "model": "llama",
        "messages": [
          {"role": "user", "content": "What is machine learning?"}
        ]
      }'
    ```
  </Tab>
</Tabs>
