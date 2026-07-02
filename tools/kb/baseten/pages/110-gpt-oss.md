# GPT-OSS
Source: https://docs.baseten.co/examples/models/llm/gpt-oss

GPT-OSS recipes: 2 variants (20B, 120B), Dense and MoE architectures.

<div>
  <a href="/examples/models/capabilities/reasoning">Reasoning</a>
  <a href="/examples/models/capabilities/tool-calling">Tool calling</a>
  <a href="/examples/models/capabilities/agentic">Agentic</a>
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
  <Tab title="20B">
    [openai/gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b) is a 20B-parameter dense model with up to 128K context.

    This preset serves GPT-OSS 20B on a single H100 using the Harmony response format, tuned for low time-to-first-token.

    <CardGroup>
      <Card title="Hardware" icon="microchip">H100</Card>
      <Card title="Engine" icon="server">TRT-LLM v2</Card>
      <Card title="Context" icon="ruler-horizontal">128K</Card>
      <Card title="Concurrency" icon="layer-group">64</Card>
    </CardGroup>

    ## Write the config

    Create and move into the project directory:

    ```sh theme={"system"}
    mkdir gpt-oss-20b-latency && cd gpt-oss-20b-latency
    ```

    Then create a file named `config.yaml` and paste the following:

    ```yaml config.yaml theme={"system"}
    model_name: "model:gpt-oss-20b preset:latency"
    build_commands:
      - python -c 'from openai_harmony import load_harmony_encoding; load_harmony_encoding("HarmonyGptOss")'
    model_metadata:
      repo_id: openai/gpt-oss-20b
      example_model_input:
        {
          "model": "openai/gpt-oss-20b",
          "messages":
            [
              {
                "role": "user",
                "content": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target. You may assume that each input would have exactly one solution, and you may not use the same element twice. You can return the answer in any order. class Solution: def twoSum(self, nums: List[int], target: int) -> List[int]:",
              },
            ],
          "stream": true,
          "max_tokens": 4096,
          "temperature": 0.5,
        }
      tags:
        - openai-compatible
    resources:
      accelerator: H100
      cpu: "1"
      memory: 10Gi
      use_gpu: true
    weights:
      - source: "hf://openai/gpt-oss-20b@main"
        mount_location: "/app/model_cache/trt_model"
    trt_llm:
      build:
        checkpoint_repository:
          repo: michaelfeil/empty-model
          revision: main
          source: HF
      inference_stack: v2
      runtime:
        enable_chunked_prefill: true
        max_batch_size: 64
        max_num_tokens: 8192
        max_seq_len: 131072
        patch_kwargs:
          model_path: /app/model_cache/trt_model
          chat_processor: harmony
          moe_expert_parallel_size: 1
          backend: pytorch
          cuda_graph_config:
            enable_padding: true
          disable_overlap_scheduler: 1
          enable_autotuner: 0
          enable_iter_perf_stats: 0
          enable_trtllm_sampler: 1
          guided_decoding_backend: xgrammar
          kv_cache_config:
            enable_block_reuse: true
            free_gpu_memory_fraction: 0.8
            event_buffer_max_size: 1024
          max_beam_width: 1
          max_input_len: 131072
          model_level_stop_words:
            - "<|call|>"
          tokenizer_limit_length: 131072
          trust_remote_code: 1
          moe_config:
            backend: CUTLASS
        served_model_name: openai/gpt-oss-20b
        tensor_parallel_size: 1
      version_overrides:
        v2_llm_version: null
    ```

    ## Key parameters

    [Baseten Inference Stack](/engines/bis-llm/overview) (BIS) reads these fields from the `trt_llm` block. Each one shapes how the engine is built and served:

    | Parameter            | Value                |
    | -------------------- | -------------------- |
    | Tensor parallel size | `1`                  |
    | Max sequence length  | `131072`             |
    | Max batch size       | `64`                 |
    | Max batched tokens   | `8192`               |
    | Chunked prefill      | `enabled`            |
    | Inference stack      | `v2`                 |
    | Served model name    | `openai/gpt-oss-20b` |

    ## Deploy

    Push the config to Baseten:

    ```sh theme={"system"}
    uvx truss push
    ```

    You should see output similar to:

    ```output theme={"system"}
    ✨ Model gpt-oss-20b-latency was successfully pushed ✨

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
            model="openai/gpt-oss-20b",
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
            "model": "openai/gpt-oss-20b",
            "messages": [
              {"role": "user", "content": "What is machine learning?"}
            ]
          }'
        ```
      </Tab>
    </Tabs>
  </Tab>

  <Tab title="120B">
    [openai/gpt-oss-120b](https://huggingface.co/openai/gpt-oss-120b) is a 120B-parameter MoE model with up to 128K context.

    This variant ships in 2 presets tuned for different goals: **H100 Throughput** for high throughput on H100 hardware, and **Throughput** for highest tokens per second. Pick the tab that matches your workload.

    <Tabs>
      <Tab title="H100 Throughput">
        This preset serves GPT-OSS 120B on H100:4 for deployments that don't have Blackwell capacity.

        <CardGroup>
          <Card title="Hardware" icon="microchip">H100 × 4</Card>
          <Card title="Engine" icon="server">vLLM (0.22.0-cu129 build)</Card>
          <Card title="Context" icon="ruler-horizontal">16K</Card>
          <Card title="Concurrency" icon="layer-group">256</Card>
        </CardGroup>

        ## Write the config

        Create and move into the project directory:

        ```sh theme={"system"}
        mkdir gpt-oss-120b-h100-throughput && cd gpt-oss-120b-h100-throughput
        ```

        Then create a file named `config.yaml` and paste the following:

        ```yaml config.yaml theme={"system"}
        model_name: "model:gpt-oss-120b preset:h100-throughput"
        model_metadata:
          description: >-
            GPT-OSS 120B on vLLM H100 × 4 throughput; weights from BDN, async scheduling and prefix caching.
          repo_id: openai/gpt-oss-120b
          tags:
            - openai-compatible
          example_model_input:
            messages:
              - role: system
                content: "You are a helpful assistant."
              - role: user
                content: "Write FizzBuzz in Python"
            stream: true
            model: "openai/gpt-oss-120b"
            max_tokens: 4096
            temperature: 0.5
        base_image:
          image: vllm/vllm-openai:v0.22.0-cu129
        build_commands:
          - mkdir -p /opt/tiktoken
          - curl -fsSL https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken -o /opt/tiktoken/o200k_base.tiktoken
          - curl -fsSL https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken -o /opt/tiktoken/cl100k_base.tiktoken
        weights:
          - source: "hf://openai/gpt-oss-120b@b5c939de8f754692c1647ca79fbf85e8c1e70f8a"
            mount_location: "/app/checkpoint/model"
            auth_secret_name: "hf_access_token"
            ignore_patterns: ["original/*", "metal/model.bin"]
        secrets:
          hf_access_token: null
        environment_variables:
          TIKTOKEN_ENCODINGS_BASE: "/opt/tiktoken"
          TIKTOKEN_RS_CACHE_DIR: "/opt/tiktoken"
          VLLM_LOGGING_LEVEL: WARNING
          VLLM_ENGINE_READY_TIMEOUT_S: "3600"
        docker_server:
          start_command: >-
            sh -c "GPU_COUNT=$(nvidia-smi --list-gpus | wc -l) && vllm serve /app/checkpoint/model
            --host 0.0.0.0
            --port 8000
            --served-model-name openai/gpt-oss-120b
            --tensor-parallel-size $GPU_COUNT
            --gpu-memory-utilization 0.90
            --max-model-len 16384
            --max-num-batched-tokens 16384
            --max-num-seqs 256
            --stream-interval 20
            --enable-chunked-prefill
            --enable-prefix-caching
            --async-scheduling
            --trust-remote-code
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

        | Flag                       | Value            | What it does                                                                                                   |
        | -------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------- |
        | `--tensor-parallel-size`   | `$GPU_COUNT`     | Number of GPUs to shard the model across.                                                                      |
        | `--gpu-memory-utilization` | `0.90`           | Fraction of GPU memory vLLM may use for weights and KV cache.                                                  |
        | `--max-model-len`          | `16384`          | Maximum context length (tokens) the server accepts per request.                                                |
        | `--max-num-batched-tokens` | `16384`          | Maximum total tokens processed per scheduler step.                                                             |
        | `--max-num-seqs`           | `256`            | Maximum number of concurrent sequences in the batch.                                                           |
        | `--stream-interval`        | `20`             | Tokens emitted per streaming chunk.                                                                            |
        | `--enable-chunked-prefill` | (no value)       | Process long prompts in chunks so decode requests keep running.                                                |
        | `--enable-prefix-caching`  | (no value)       | Reuse KV cache across requests that share a prefix.                                                            |
        | `--async-scheduling`       | (no value)       | Overlap scheduling with GPU execution to hide scheduler latency.                                               |
        | `--trust-remote-code`      | (no value)       | Execute model-specific Python from the checkpoint (required for many Qwen, Phi, and custom architectures).     |
        | `--load-format`            | `runai_streamer` | Weight loading backend. **runai\_streamer:** Stream weights from object storage without materializing to disk. |

        ## Deploy

        Push the config to Baseten:

        ```sh theme={"system"}
        uvx truss push
        ```

        You should see output similar to:

        ```output theme={"system"}
        ✨ Model gpt-oss-120b-h100-throughput was successfully pushed ✨

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
                model="openai/gpt-oss-120b",
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
                "model": "openai/gpt-oss-120b",
                "messages": [
                  {"role": "user", "content": "What is machine learning?"}
                ]
              }'
            ```
          </Tab>
        </Tabs>
      </Tab>

      <Tab title="Throughput">
        This preset serves GPT-OSS 120B on B200:4 with FP8 KV cache and FlashInfer MXFP4+MXFP8 MoE kernels, optimized for maximum throughput on Blackwell.

        <CardGroup>
          <Card title="Hardware" icon="microchip">B200 × 4</Card>
          <Card title="Engine" icon="server">vLLM 0.22.0</Card>
          <Card title="Context" icon="ruler-horizontal">8K</Card>
          <Card title="Concurrency" icon="layer-group">256</Card>
        </CardGroup>

        ## Write the config

        Create and move into the project directory:

        ```sh theme={"system"}
        mkdir gpt-oss-120b-throughput && cd gpt-oss-120b-throughput
        ```

        Then create a file named `config.yaml` and paste the following:

        ```yaml config.yaml theme={"system"}
        model_name: "model:gpt-oss-120b preset:throughput"
        model_metadata:
          description: >-
            GPT-OSS 120B on vLLM Blackwell (B200 × 4), Harmony recipe with FlashInfer MoE MXFP paths.
          repo_id: openai/gpt-oss-120b
          tags:
            - openai-compatible
          example_model_input:
            messages:
              - role: user
                content: "Write FizzBuzz in Python."
            stream: true
            model: openai/gpt-oss-120b
            max_tokens: 4096
            temperature: 0.5
        base_image:
          image: vllm/vllm-openai:v0.22.0
        build_commands:
          - mkdir -p /opt/tiktoken
          - curl -fsSL https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken -o /opt/tiktoken/o200k_base.tiktoken
          - curl -fsSL https://openaipublic.blob.core.windows.net/encodings/cl100k_base.tiktoken -o /opt/tiktoken/cl100k_base.tiktoken
        weights:
          - source: "hf://openai/gpt-oss-120b@b5c939de8f754692c1647ca79fbf85e8c1e70f8a"
            mount_location: "/app/checkpoint/model"
            auth_secret_name: "hf_access_token"
            ignore_patterns: ["original/*", "metal/model.bin"]
        secrets:
          hf_access_token: null
        environment_variables:
          TIKTOKEN_ENCODINGS_BASE: "/opt/tiktoken"
          TIKTOKEN_RS_CACHE_DIR: "/opt/tiktoken"
          VLLM_LOGGING_LEVEL: WARNING
          VLLM_ENGINE_READY_TIMEOUT_S: "3600"
          VLLM_USE_FLASHINFER_MOE_MXFP4_MXFP8: "1"
        docker_server:
          start_command: >-
            sh -c "GPU_COUNT=$(nvidia-smi --list-gpus | wc -l) && vllm serve /app/checkpoint/model
            --host 0.0.0.0
            --port 8000
            --served-model-name gpt-oss-120b
            --tensor-parallel-size $GPU_COUNT
            --gpu-memory-utilization 0.95
            --max-model-len 8192
            --max-num-batched-tokens 8192
            --max-num-seqs 256
            --cuda-graph-capture-size 2048
            --stream-interval 20
            --kv-cache-dtype fp8
            --enable-prefix-caching
            --async-scheduling
            --trust-remote-code
            --load-format runai_streamer"
          readiness_endpoint: /health
          liveness_endpoint: /health
          predict_endpoint: /v1/chat/completions
          server_port: 8000
        resources:
          accelerator: B200:4
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

        | Flag                        | Value            | What it does                                                                                                   |
        | --------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------- |
        | `--tensor-parallel-size`    | `$GPU_COUNT`     | Number of GPUs to shard the model across.                                                                      |
        | `--gpu-memory-utilization`  | `0.95`           | Fraction of GPU memory vLLM may use for weights and KV cache.                                                  |
        | `--max-model-len`           | `8192`           | Maximum context length (tokens) the server accepts per request.                                                |
        | `--max-num-batched-tokens`  | `8192`           | Maximum total tokens processed per scheduler step.                                                             |
        | `--max-num-seqs`            | `256`            | Maximum number of concurrent sequences in the batch.                                                           |
        | `--cuda-graph-capture-size` | `2048`           | Batch size ceiling for CUDA graph capture (improves decode latency).                                           |
        | `--stream-interval`         | `20`             | Tokens emitted per streaming chunk.                                                                            |
        | `--kv-cache-dtype`          | `fp8`            | KV cache numeric precision. **fp8:** \~2× KV cache density with negligible quality impact on most models.      |
        | `--enable-prefix-caching`   | (no value)       | Reuse KV cache across requests that share a prefix.                                                            |
        | `--async-scheduling`        | (no value)       | Overlap scheduling with GPU execution to hide scheduler latency.                                               |
        | `--trust-remote-code`       | (no value)       | Execute model-specific Python from the checkpoint (required for many Qwen, Phi, and custom architectures).     |
        | `--load-format`             | `runai_streamer` | Weight loading backend. **runai\_streamer:** Stream weights from object storage without materializing to disk. |

        ## Deploy

        Push the config to Baseten:

        ```sh theme={"system"}
        uvx truss push
        ```

        You should see output similar to:

        ```output theme={"system"}
        ✨ Model gpt-oss-120b-throughput was successfully pushed ✨

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
                model="gpt-oss-120b",
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
                "model": "gpt-oss-120b",
                "messages": [
                  {"role": "user", "content": "What is machine learning?"}
                ]
              }'
            ```
          </Tab>
        </Tabs>
      </Tab>
    </Tabs>
  </Tab>
</Tabs>
