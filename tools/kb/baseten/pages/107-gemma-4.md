# Gemma 4
Source: https://docs.baseten.co/examples/models/llm/gemma-4

Gemma 4 recipes: 4 variants (E2B, E4B, 26B A4B, 31B), Dense and MoE architectures.

<div>
  <a href="/examples/models/capabilities/reasoning">Reasoning</a>
  <a href="/examples/models/capabilities/tool-calling">Tool calling</a>
  <a href="/examples/models/capabilities/multimodal-image">Multimodal (image)</a>
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

Pick the model you want to deploy. Each tab is a self-contained recipe.

<Tabs>
  <Tab title="E2B">
    [google/gemma-4-E2B-it](https://huggingface.co/google/gemma-4-E2B-it) is a 2B-parameter dense model with up to 125K context.

    This preset serves Gemma 4 E2B on a single L4, the lowest-cost deployment in the Model Library.

    <CardGroup>
      <Card title="Hardware" icon="microchip">L4</Card>
      <Card title="Engine" icon="server">vLLM (0.22.0-cu129 build)</Card>
      <Card title="Context" icon="ruler-horizontal">125K</Card>
      <Card title="Concurrency" icon="layer-group">8</Card>
    </CardGroup>

    ## Write the config

    Create and move into the project directory:

    ```sh theme={"system"}
    mkdir gemma-4-E2B-it-latency && cd gemma-4-E2B-it-latency
    ```

    Then create a file named `config.yaml` and paste the following:

    ```yaml config.yaml theme={"system"}
    model_name: model:gemma-4-E2B-it preset:latency
    model_metadata:
      description: >-
        Gemma 4 multimodal instruct (preview E2B), OpenAI-compatible chat with vision via vLLM on L4.
      repo_id: google/gemma-4-E2B-it
      example_model_input:
        model: google/gemma-4-E2B-it
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
      - source: "hf://google/gemma-4-E2B-it@main"
        mount_location: "/app/checkpoint/model"
        auth_secret_name: "hf_access_token"
    secrets:
      hf_access_token: null
    docker_server:
      start_command: >-
        sh -c "GPU_COUNT=$(nvidia-smi --list-gpus | wc -l) && vllm serve /app/checkpoint/model
        --tensor-parallel-size $GPU_COUNT
        --served-model-name google/gemma-4-E2B-it
        --max-num-seqs 16
        --max-model-len auto
        --limit-mm-per-prompt.image 1
        --gpu-memory-utilization 0.9
        --async-scheduling
        --trust-remote-code
        --enable-auto-tool-choice
        --enable-prefix-caching
        --reasoning-parser gemma4
        --tool-call-parser gemma4
        --load-format runai_streamer"
      readiness_endpoint: /health
      liveness_endpoint: /health
      predict_endpoint: /v1/chat/completions
      server_port: 8000
    environment_variables:
      VLLM_LOGGING_LEVEL: WARNING
      VLLM_ENGINE_READY_TIMEOUT_S: "3600"
    resources:
      accelerator: L4
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

    | Flag                          | Value            | What it does                                                                                                   |
    | ----------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------- |
    | `--tensor-parallel-size`      | `$GPU_COUNT`     | Number of GPUs to shard the model across.                                                                      |
    | `--max-num-seqs`              | `16`             | Maximum number of concurrent sequences in the batch.                                                           |
    | `--max-model-len`             | `auto`           | Maximum context length (tokens) the server accepts per request.                                                |
    | `--limit-mm-per-prompt.image` | `1`              | Maximum number of image inputs per prompt.                                                                     |
    | `--gpu-memory-utilization`    | `0.9`            | Fraction of GPU memory vLLM may use for weights and KV cache.                                                  |
    | `--async-scheduling`          | (no value)       | Overlap scheduling with GPU execution to hide scheduler latency.                                               |
    | `--trust-remote-code`         | (no value)       | Execute model-specific Python from the checkpoint (required for many Qwen, Phi, and custom architectures).     |
    | `--enable-auto-tool-choice`   | (no value)       | Let the model choose when to call tools without requiring `tool_choice: "required"`.                           |
    | `--enable-prefix-caching`     | (no value)       | Reuse KV cache across requests that share a prefix.                                                            |
    | `--reasoning-parser`          | `gemma4`         | Server-side parser that separates reasoning output into `reasoning_content`.                                   |
    | `--tool-call-parser`          | `gemma4`         | Server-side parser that emits structured `tool_calls` on the response.                                         |
    | `--load-format`               | `runai_streamer` | Weight loading backend. **runai\_streamer:** Stream weights from object storage without materializing to disk. |

    ## Deploy

    Push the config to Baseten:

    ```sh theme={"system"}
    uvx truss push
    ```

    You should see output similar to:

    ```output theme={"system"}
    ✨ Model gemma-4-E2B-it-latency was successfully pushed ✨

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
            model="google/gemma-4-E2B-it",
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
            "model": "google/gemma-4-E2B-it",
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
        model="google/gemma-4-E2B-it",
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
        model="google/gemma-4-E2B-it",
        messages=[
            {"role": "user", "content": "What's the weather in Paris?"}
        ],
        tools=tools,
    )
    print(response.choices[0].message.tool_calls)
    ```
  </Tab>

  <Tab title="E4B">
    [google/gemma-4-E4B-it](https://huggingface.co/google/gemma-4-E4B-it) is a 4B-parameter dense model with up to 125K context.

    This preset serves Gemma 4 E4B on a single H100.

    <CardGroup>
      <Card title="Hardware" icon="microchip">H100</Card>
      <Card title="Engine" icon="server">vLLM (0.22.0-cu129 build)</Card>
      <Card title="Context" icon="ruler-horizontal">125K</Card>
      <Card title="Concurrency" icon="layer-group">8</Card>
    </CardGroup>

    ## Write the config

    Create and move into the project directory:

    ```sh theme={"system"}
    mkdir gemma-4-E4B-it-latency && cd gemma-4-E4B-it-latency
    ```

    Then create a file named `config.yaml` and paste the following:

    ```yaml config.yaml theme={"system"}
    model_name: model:gemma-4-E4B-it preset:latency
    model_metadata:
      description: >-
        Gemma 4 multimodal instruct (preview E4B), OpenAI-compatible chat with vision via vLLM.
      repo_id: google/gemma-4-E4B-it
      example_model_input:
        model: google/gemma-4-E4B-it
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
      - source: "hf://google/gemma-4-E4B-it@main"
        mount_location: "/app/checkpoint/model"
        auth_secret_name: "hf_access_token"
    secrets:
      hf_access_token: null
    docker_server:
      start_command: >-
        sh -c "GPU_COUNT=$(nvidia-smi --list-gpus | wc -l) && vllm serve /app/checkpoint/model
        --tensor-parallel-size $GPU_COUNT
        --served-model-name google/gemma-4-E4B-it
        --max-num-seqs 16
        --max-model-len auto
        --limit-mm-per-prompt.image 1
        --gpu-memory-utilization 0.9
        --async-scheduling
        --trust-remote-code
        --enable-auto-tool-choice
        --enable-prefix-caching
        --reasoning-parser gemma4
        --tool-call-parser gemma4
        --load-format runai_streamer"
      readiness_endpoint: /health
      liveness_endpoint: /health
      predict_endpoint: /v1/chat/completions
      server_port: 8000
    environment_variables:
      VLLM_LOGGING_LEVEL: WARNING
      VLLM_ENGINE_READY_TIMEOUT_S: "3600"
    resources:
      accelerator: H100
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

    | Flag                          | Value            | What it does                                                                                                   |
    | ----------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------- |
    | `--tensor-parallel-size`      | `$GPU_COUNT`     | Number of GPUs to shard the model across.                                                                      |
    | `--max-num-seqs`              | `16`             | Maximum number of concurrent sequences in the batch.                                                           |
    | `--max-model-len`             | `auto`           | Maximum context length (tokens) the server accepts per request.                                                |
    | `--limit-mm-per-prompt.image` | `1`              | Maximum number of image inputs per prompt.                                                                     |
    | `--gpu-memory-utilization`    | `0.9`            | Fraction of GPU memory vLLM may use for weights and KV cache.                                                  |
    | `--async-scheduling`          | (no value)       | Overlap scheduling with GPU execution to hide scheduler latency.                                               |
    | `--trust-remote-code`         | (no value)       | Execute model-specific Python from the checkpoint (required for many Qwen, Phi, and custom architectures).     |
    | `--enable-auto-tool-choice`   | (no value)       | Let the model choose when to call tools without requiring `tool_choice: "required"`.                           |
    | `--enable-prefix-caching`     | (no value)       | Reuse KV cache across requests that share a prefix.                                                            |
    | `--reasoning-parser`          | `gemma4`         | Server-side parser that separates reasoning output into `reasoning_content`.                                   |
    | `--tool-call-parser`          | `gemma4`         | Server-side parser that emits structured `tool_calls` on the response.                                         |
    | `--load-format`               | `runai_streamer` | Weight loading backend. **runai\_streamer:** Stream weights from object storage without materializing to disk. |

    ## Deploy

    Push the config to Baseten:

    ```sh theme={"system"}
    uvx truss push
    ```

    You should see output similar to:

    ```output theme={"system"}
    ✨ Model gemma-4-E4B-it-latency was successfully pushed ✨

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
            model="google/gemma-4-E4B-it",
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
            "model": "google/gemma-4-E4B-it",
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
        model="google/gemma-4-E4B-it",
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
        model="google/gemma-4-E4B-it",
        messages=[
            {"role": "user", "content": "What's the weather in Paris?"}
        ],
        tools=tools,
    )
    print(response.choices[0].message.tool_calls)
    ```
  </Tab>

  <Tab title="26B A4B">
    [google/gemma-4-26B-A4B-it](https://huggingface.co/google/gemma-4-26B-A4B-it) is a 26B-parameter MoE model (4B active per token) with up to 256K context.

    This preset serves Gemma 4 26B A4B on H100:2 with FP8 dynamic quantization.

    <CardGroup>
      <Card title="Hardware" icon="microchip">H100 × 2</Card>
      <Card title="Engine" icon="server">vLLM (0.22.0-cu129 build)</Card>
      <Card title="Context" icon="ruler-horizontal">256K</Card>
      <Card title="Concurrency" icon="layer-group">8</Card>
    </CardGroup>

    ## Write the config

    Create and move into the project directory:

    ```sh theme={"system"}
    mkdir gemma-4-26B-A4B-it-latency && cd gemma-4-26B-A4B-it-latency
    ```

    Then create a file named `config.yaml` and paste the following:

    ```yaml config.yaml theme={"system"}
    model_name: model:gemma-4-26B-A4B-it preset:latency
    model_metadata:
      description: >-
        Gemma 4 multimodal instruct (26B MOE FP8 dynamique), speculative decoding Eagle3 via vLLM.
      repo_id: RedHatAI/gemma-4-26B-A4B-it-FP8-Dynamic
      example_model_input:
        model: google/gemma-4-26B-A4B-it
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
      - source: "hf://RedHatAI/gemma-4-26B-A4B-it-FP8-Dynamic@main"
        mount_location: "/app/checkpoint/model"
        auth_secret_name: "hf_access_token"
    secrets:
      hf_access_token: null
    docker_server:
      start_command: >-
        sh -c "GPU_COUNT=$(nvidia-smi --list-gpus | wc -l) && vllm serve /app/checkpoint/model
        --tensor-parallel-size $GPU_COUNT
        --served-model-name google/gemma-4-26B-A4B-it
        --max-num-seqs 16
        --max-model-len auto
        --limit-mm-per-prompt.image 1
        --gpu-memory-utilization 0.9
        --enable-prefix-caching
        --speculative-config.model RedHatAI/gemma-4-26B-A4B-it-speculator.eagle3
        --speculative-config.num_speculative_tokens 3
        --speculative-config.method eagle3
        --trust-remote-code
        --enable-auto-tool-choice
        --reasoning-parser gemma4
        --tool-call-parser gemma4
        --load-format runai_streamer"
      readiness_endpoint: /health
      liveness_endpoint: /health
      predict_endpoint: /v1/chat/completions
      server_port: 8000
    environment_variables:
      VLLM_LOGGING_LEVEL: WARNING
      VLLM_ENGINE_READY_TIMEOUT_S: "3600"
    resources:
      accelerator: H100:2
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

    | Flag                                          | Value                                           | What it does                                                                                                   |
    | --------------------------------------------- | ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
    | `--tensor-parallel-size`                      | `$GPU_COUNT`                                    | Number of GPUs to shard the model across.                                                                      |
    | `--max-num-seqs`                              | `16`                                            | Maximum number of concurrent sequences in the batch.                                                           |
    | `--max-model-len`                             | `auto`                                          | Maximum context length (tokens) the server accepts per request.                                                |
    | `--limit-mm-per-prompt.image`                 | `1`                                             | Maximum number of image inputs per prompt.                                                                     |
    | `--gpu-memory-utilization`                    | `0.9`                                           | Fraction of GPU memory vLLM may use for weights and KV cache.                                                  |
    | `--enable-prefix-caching`                     | (no value)                                      | Reuse KV cache across requests that share a prefix.                                                            |
    | `--speculative-config.model`                  | `RedHatAI/gemma-4-26B-A4B-it-speculator.eagle3` | Hugging Face repo for the draft speculator checkpoint.                                                         |
    | `--speculative-config.num_speculative_tokens` | `3`                                             | Number of tokens the draft speculator proposes per step.                                                       |
    | `--speculative-config.method`                 | `eagle3`                                        | Speculative decoding method. **eagle3:** EAGLE v3 speculative decoding.                                        |
    | `--trust-remote-code`                         | (no value)                                      | Execute model-specific Python from the checkpoint (required for many Qwen, Phi, and custom architectures).     |
    | `--enable-auto-tool-choice`                   | (no value)                                      | Let the model choose when to call tools without requiring `tool_choice: "required"`.                           |
    | `--reasoning-parser`                          | `gemma4`                                        | Server-side parser that separates reasoning output into `reasoning_content`.                                   |
    | `--tool-call-parser`                          | `gemma4`                                        | Server-side parser that emits structured `tool_calls` on the response.                                         |
    | `--load-format`                               | `runai_streamer`                                | Weight loading backend. **runai\_streamer:** Stream weights from object storage without materializing to disk. |

    ## Deploy

    Push the config to Baseten:

    ```sh theme={"system"}
    uvx truss push
    ```

    You should see output similar to:

    ```output theme={"system"}
    ✨ Model gemma-4-26B-A4B-it-latency was successfully pushed ✨

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
            model="google/gemma-4-26B-A4B-it",
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
            "model": "google/gemma-4-26B-A4B-it",
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
        model="google/gemma-4-26B-A4B-it",
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
        model="google/gemma-4-26B-A4B-it",
        messages=[
            {"role": "user", "content": "What's the weather in Paris?"}
        ],
        tools=tools,
    )
    print(response.choices[0].message.tool_calls)
    ```
  </Tab>

  <Tab title="31B">
    [google/gemma-4-31B-it](https://huggingface.co/google/gemma-4-31B-it) is a 31B-parameter dense model with up to 256K context.

    This variant ships in 2 presets tuned for different goals: **Latency** for lowest time-to-first-token, and **Throughput** for highest tokens per second. Pick the tab that matches your workload.

    <Tabs>
      <Tab title="Latency">
        This preset serves Gemma 4 31B on H100:2 with FP8 block quantization.

        <CardGroup>
          <Card title="Hardware" icon="microchip">H100 × 2</Card>
          <Card title="Engine" icon="server">vLLM (0.22.0-cu129 build)</Card>
          <Card title="Context" icon="ruler-horizontal">256K</Card>
          <Card title="Concurrency" icon="layer-group">8</Card>
        </CardGroup>

        ## Write the config

        Create and move into the project directory:

        ```sh theme={"system"}
        mkdir gemma-4-31B-it-latency && cd gemma-4-31B-it-latency
        ```

        Then create a file named `config.yaml` and paste the following:

        ```yaml config.yaml theme={"system"}
        model_name: model:gemma-4-31B-it preset:latency
        model_metadata:
          description: >-
            Gemma 4 multimodal instruct (FP8), OpenAI-compatible chat with vision via vLLM.
          repo_id: RedHatAI/gemma-4-31B-it-FP8-block
          example_model_input:
            model: google/gemma-4-31B-it
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
          - source: "hf://RedHatAI/gemma-4-31B-it-FP8-block@main"
            mount_location: "/app/checkpoint/model"
            auth_secret_name: "hf_access_token"
        secrets:
          hf_access_token: null
        docker_server:
          start_command: >-
            sh -c "GPU_COUNT=$(nvidia-smi --list-gpus | wc -l) && vllm serve /app/checkpoint/model
            --tensor-parallel-size $GPU_COUNT
            --served-model-name google/gemma-4-31B-it
            --max-num-seqs 16
            --max-model-len auto
            --limit-mm-per-prompt.image 1
            --gpu-memory-utilization 0.9
            --enable-prefix-caching
            --speculative-config.model RedHatAI/gemma-4-31B-it-speculator.eagle3
            --speculative-config.num_speculative_tokens 3
            --speculative-config.method eagle3
            --trust-remote-code
            --enable-auto-tool-choice
            --reasoning-parser gemma4
            --tool-call-parser gemma4
            --load-format runai_streamer"
          readiness_endpoint: /health
          liveness_endpoint: /health
          predict_endpoint: /v1/chat/completions
          server_port: 8000
        environment_variables:
          VLLM_LOGGING_LEVEL: WARNING
          VLLM_ENGINE_READY_TIMEOUT_S: "3600"
        resources:
          accelerator: H100:2
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

        | Flag                                          | Value                                       | What it does                                                                                                   |
        | --------------------------------------------- | ------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
        | `--tensor-parallel-size`                      | `$GPU_COUNT`                                | Number of GPUs to shard the model across.                                                                      |
        | `--max-num-seqs`                              | `16`                                        | Maximum number of concurrent sequences in the batch.                                                           |
        | `--max-model-len`                             | `auto`                                      | Maximum context length (tokens) the server accepts per request.                                                |
        | `--limit-mm-per-prompt.image`                 | `1`                                         | Maximum number of image inputs per prompt.                                                                     |
        | `--gpu-memory-utilization`                    | `0.9`                                       | Fraction of GPU memory vLLM may use for weights and KV cache.                                                  |
        | `--enable-prefix-caching`                     | (no value)                                  | Reuse KV cache across requests that share a prefix.                                                            |
        | `--speculative-config.model`                  | `RedHatAI/gemma-4-31B-it-speculator.eagle3` | Hugging Face repo for the draft speculator checkpoint.                                                         |
        | `--speculative-config.num_speculative_tokens` | `3`                                         | Number of tokens the draft speculator proposes per step.                                                       |
        | `--speculative-config.method`                 | `eagle3`                                    | Speculative decoding method. **eagle3:** EAGLE v3 speculative decoding.                                        |
        | `--trust-remote-code`                         | (no value)                                  | Execute model-specific Python from the checkpoint (required for many Qwen, Phi, and custom architectures).     |
        | `--enable-auto-tool-choice`                   | (no value)                                  | Let the model choose when to call tools without requiring `tool_choice: "required"`.                           |
        | `--reasoning-parser`                          | `gemma4`                                    | Server-side parser that separates reasoning output into `reasoning_content`.                                   |
        | `--tool-call-parser`                          | `gemma4`                                    | Server-side parser that emits structured `tool_calls` on the response.                                         |
        | `--load-format`                               | `runai_streamer`                            | Weight loading backend. **runai\_streamer:** Stream weights from object storage without materializing to disk. |

        ## Deploy

        Push the config to Baseten:

        ```sh theme={"system"}
        uvx truss push
        ```

        You should see output similar to:

        ```output theme={"system"}
        ✨ Model gemma-4-31B-it-latency was successfully pushed ✨

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
                model="google/gemma-4-31B-it",
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
                "model": "google/gemma-4-31B-it",
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
            model="google/gemma-4-31B-it",
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
            model="google/gemma-4-31B-it",
            messages=[
                {"role": "user", "content": "What's the weather in Paris?"}
            ],
            tools=tools,
        )
        print(response.choices[0].message.tool_calls)
        ```
      </Tab>

      <Tab title="Throughput">
        <CardGroup>
          <Card title="Hardware" icon="microchip">RTX\_PRO\_6000</Card>
          <Card title="Engine" icon="server">vLLM 0.22.1</Card>
          <Card title="Context" icon="ruler-horizontal">128K</Card>
          <Card title="Concurrency" icon="layer-group">64</Card>
        </CardGroup>

        ## Write the config

        Create and move into the project directory:

        ```sh theme={"system"}
        mkdir gemma-4-31B-it && cd gemma-4-31B-it
        ```

        Then create a file named `config.yaml` and paste the following:

        ```yaml config.yaml theme={"system"}
        model_name: model:gemma-4-31B-it preset:throughput
        model_metadata:
          description: >-
            Gemma 4 multimodal instruct (NVFP4), OpenAI-compatible chat with vision via vLLM on RTX PRO 6000.
          repo_id: nvidia/Gemma-4-31B-IT-NVFP4
          example_model_input:
            model: google/gemma-4-31B-it
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
          image: vllm/vllm-openai:v0.22.1
        weights:
          - source: "hf://nvidia/Gemma-4-31B-IT-NVFP4@main"
            mount_location: "/app/checkpoint/gemma"
            auth_secret_name: "hf_access_token"
        secrets:
          hf_access_token: null
        docker_server:
          start_command: >-
            sh -c "GPU_COUNT=$(nvidia-smi --list-gpus | wc -l) && vllm serve /app/checkpoint/gemma
            --tensor-parallel-size $GPU_COUNT
            --served-model-name google/gemma-4-31B-it
            --max-num-seqs 64
            --max-model-len 131072
            --kv-cache-dtype fp8
            --enable-chunked-prefill
            --limit-mm-per-prompt.image 1
            --enable-prefix-caching
            --trust-remote-code
            --enable-auto-tool-choice
            --reasoning-parser gemma4
            --tool-call-parser gemma4
            --load-format runai_streamer"
          readiness_endpoint: /health
          liveness_endpoint: /health
          predict_endpoint: /v1/chat/completions
          server_port: 8000
        resources:
          accelerator: RTX_PRO_6000
          use_gpu: true
        runtime:
          health_checks:
            restart_check_delay_seconds: 1800
            restart_threshold_seconds: 1200
            stop_traffic_threshold_seconds: 120
          predict_concurrency: 64
        ```

        ## Flags

        The `start_command` passes these flags to the engine. Each one controls a runtime or serving behavior:

        | Flag                          | Value            | What it does                                                                                                   |
        | ----------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------- |
        | `--tensor-parallel-size`      | `$GPU_COUNT`     | Number of GPUs to shard the model across.                                                                      |
        | `--max-num-seqs`              | `64`             | Maximum number of concurrent sequences in the batch.                                                           |
        | `--max-model-len`             | `131072`         | Maximum context length (tokens) the server accepts per request.                                                |
        | `--kv-cache-dtype`            | `fp8`            | KV cache numeric precision. **fp8:** \~2× KV cache density with negligible quality impact on most models.      |
        | `--enable-chunked-prefill`    | (no value)       | Process long prompts in chunks so decode requests keep running.                                                |
        | `--limit-mm-per-prompt.image` | `1`              | Maximum number of image inputs per prompt.                                                                     |
        | `--enable-prefix-caching`     | (no value)       | Reuse KV cache across requests that share a prefix.                                                            |
        | `--trust-remote-code`         | (no value)       | Execute model-specific Python from the checkpoint (required for many Qwen, Phi, and custom architectures).     |
        | `--enable-auto-tool-choice`   | (no value)       | Let the model choose when to call tools without requiring `tool_choice: "required"`.                           |
        | `--reasoning-parser`          | `gemma4`         | Server-side parser that separates reasoning output into `reasoning_content`.                                   |
        | `--tool-call-parser`          | `gemma4`         | Server-side parser that emits structured `tool_calls` on the response.                                         |
        | `--load-format`               | `runai_streamer` | Weight loading backend. **runai\_streamer:** Stream weights from object storage without materializing to disk. |

        ## Deploy

        Push the config to Baseten:

        ```sh theme={"system"}
        uvx truss push
        ```

        You should see output similar to:

        ```output theme={"system"}
        ✨ Model gemma-4-31B-it was successfully pushed ✨

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
                model="google/gemma-4-31B-it",
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
                "model": "google/gemma-4-31B-it",
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
            model="google/gemma-4-31B-it",
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
            model="google/gemma-4-31B-it",
            messages=[
                {"role": "user", "content": "What's the weather in Paris?"}
            ],
            tools=tools,
        )
        print(response.choices[0].message.tool_calls)
        ```
      </Tab>
    </Tabs>
  </Tab>
</Tabs>
