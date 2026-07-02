# Nemotron 3
Source: https://docs.baseten.co/examples/models/llm/nemotron-3

NVIDIA's Nemotron 3 Super 120B A12B Mixture-of-Experts model. Runs on B200:4 through Baseten Inference Stack with MTP speculative decoding and the NVFP4-quantized checkpoint, tuned for high-throughput reasoning.

<div>
  <a href="/examples/models/capabilities/reasoning">Reasoning</a>
  <a href="/examples/models/capabilities/tool-calling">Tool calling</a>
  <a href="/examples/models/capabilities/agentic">Agentic</a>
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

[nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4) is a 120B-parameter MoE model with 12B active per token.

This preset serves Nemotron 3 Super 120B A12B on B200:4 through [Baseten Inference Stack](/engines/bis-llm/overview) (TensorRT-LLM) with NVFP4 weights, expert parallelism, and MTP speculative decoding. It targets high-throughput reasoning.

<CardGroup>
  <Card title="Hardware" icon="microchip">B200 × 4</Card>
  <Card title="Engine" icon="server">TRT-LLM v2</Card>
  <Card title="Context" icon="ruler-horizontal">128K</Card>
  <Card title="Concurrency" icon="layer-group">32</Card>
</CardGroup>

## Write the config

Create and move into the project directory:

```sh theme={"system"}
mkdir nemotron-3-super-120b-a12b-throughput && cd nemotron-3-super-120b-a12b-throughput
```

Then create a file named `config.yaml` and paste the following:

```yaml config.yaml theme={"system"}
model_name: model:nemotron-3-super-120b-a12b preset:throughput

model_metadata:
  example_model_input:
    model: "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4"
    max_tokens: 512
    messages:
      - role: user
        content: Tell me everything you know about optimized inference.
    stream: true
    temperature: 0.5
  tags:
    - openai-compatible

resources:
  accelerator: B200:4
  cpu: "1"
  memory: 10Gi
  use_gpu: true

environment_variables:
  PYTORCH_CUDA_ALLOC_CONF: "expandable_segments:True"
  TRTLLM_ENABLE_PDL: "1"
  BAD_TOKEN_ID_SEQ_CHECK_ENABLED: "1"
  ENABLE_B10_LOOKAHEAD: "0"

secrets:
  hf_access_token: null

trt_llm:
  inference_stack: v2
  build:
    checkpoint_repository:
      repo: nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4
      revision: main
      source: HF
      runtime_secret_name: hf_access_token
  runtime:
    enable_chunked_prefill: true
    max_batch_size: 32
    max_num_tokens: 16384
    max_seq_len: 131072
    tensor_parallel_size: 4
    served_model_name: nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4
    patch_kwargs:
      reasoning_parser: nemotron3
      tool_call_parser: qwen3_coder
      tokenizer_limit_length: 131072
      arguments_as_json: true
      engine_config:
        backend: pytorch
        enable_chunked_prefill: true
        enable_iter_perf_stats: true
        max_batch_size: 32
        max_beam_width: 1
        max_input_len: 131072
        max_num_tokens: 16384
        max_seq_len: 131072
        trust_remote_code: true
        moe_expert_parallel_size: 4
        cuda_graph_config:
          enable_padding: true
          max_batch_size: 32
        kv_cache_config:
          dtype: fp8
          enable_block_reuse: false
          free_gpu_memory_fraction: 0.8
          mamba_ssm_cache_dtype: float32
        moe_config:
          backend: TRTLLM
        speculative_config:
          decoding_type: MTP
          num_nextn_predict_layers: 3
          allow_advanced_sampling: true
```

This config tells Baseten to compile a TensorRT-LLM engine for Nemotron 3 Super 120B A12B on four B200 GPUs with NVFP4-quantized weights, wiring the Qwen3-coder tool-call parser and Nemotron 3 reasoning parser into the engine config. Expert parallelism across all four GPUs, MTP speculative decoding with three draft tokens, and chunked prefill combine to push high reasoning throughput, serving up to a 128K context window.

## Key parameters

[Baseten Inference Stack](/engines/bis-llm/overview) (BIS) reads these fields from the `trt_llm` block. Each one shapes how the engine is built and served:

| Parameter            | Value                                            |
| -------------------- | ------------------------------------------------ |
| Tensor parallel size | `4`                                              |
| Max sequence length  | `131072`                                         |
| Max batch size       | `32`                                             |
| Max batched tokens   | `16384`                                          |
| Chunked prefill      | `enabled`                                        |
| Inference stack      | `v2`                                             |
| Served model name    | `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4` |

## Deploy

Push the config to Baseten:

```sh theme={"system"}
uvx truss push
```

You should see output similar to:

```output theme={"system"}
✨ Model nemotron-3-super-120b-a12b-throughput was successfully pushed ✨

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
        model="nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4",
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
        "model": "nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4",
        "messages": [
          {"role": "user", "content": "What is machine learning?"}
        ]
      }'
    ```
  </Tab>
</Tabs>
