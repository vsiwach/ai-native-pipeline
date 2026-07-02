# Supported base models
Source: https://docs.baseten.co/loops/supported-models

Hugging Face base models Loops accepts, with sequence-length limits.

Each row below is a Hugging Face repo ID you can pass as `base_model` when starting a Loops run, along with the maximum supported sequence length. Baseten adds rows as it validates new models end to end.

## Models

| Model                                           | Max sequence length |
| ----------------------------------------------- | ------------------- |
| `Qwen/Qwen3-0.6B`                               | 8,192               |
| `Qwen/Qwen3-4B-Instruct-2507`                   | 40,960              |
| `Qwen/Qwen3-8B`                                 | 131,072             |
| `Qwen/Qwen3-30B-A3B-Instruct-2507`              | 131,072             |
| `Qwen/Qwen3.5-0.8B`                             | 131,072             |
| `Qwen/Qwen3.5-2B`                               | 131,072             |
| `Qwen/Qwen3.5-4B`                               | 131,072             |
| `Qwen/Qwen3.5-9B`                               | 131,072             |
| `Qwen/Qwen3.5-27B`                              | 131,072             |
| `Qwen/Qwen3.5-35B-A3B`                          | 131,072             |
| `Qwen/Qwen3.5-122B-A10B`                        | 131,072             |
| `Qwen/Qwen3.5-397B-A17B`                        | 131,072             |
| `Qwen/Qwen3.6-27B`                              | 131,072             |
| `Qwen/Qwen3.6-35B-A3B`                          | 131,072             |
| `deepseek-ai/DeepSeek-V4-Flash`                 | 131,072             |
| `moonshotai/Kimi-K2.6`                          | 131,072             |
| `moonshotai/Kimi-K2.7-Code`                     | 131,072             |
| `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16` | 262,144             |
| `zai-org/GLM-5.2-FP8`                           | 65,536              |

## List supported models

Query the `/v1/loops/capabilities` endpoint for the current list of base models and their maximum sequence lengths:

<CodeGroup>
  ```bash Request theme={"system"}
  curl https://api.baseten.co/v1/loops/capabilities \
    -H "Authorization: Bearer $BASETEN_API_KEY"
  ```

  ```json Output theme={"system"}
  {
    "supported_models": [
      {"model_name": "Qwen/Qwen3-0.6B", "max_context_length": 8192},
      {"model_name": "Qwen/Qwen3-30B-A3B-Instruct-2507", "max_context_length": 131072},
      ...
    ]
  }
  ```
</CodeGroup>

The endpoint lists the base models your workspace has access to, so its response is the source of truth for what you can pass as `base_model`, even where it differs from the table above. See [`GET /v1/loops/capabilities`](/reference/loops-api/server/get-capabilities) for the full route reference.

## Pass a model to Loops

Pass the table value verbatim as `base_model` through any of the following entry points:

* The Python SDK, using `tinker.ServiceClient.create_lora_training_client(base_model=...)`. See the [Loops quickstart](/loops/quickstart).
* The HTTP API, using [`POST /v1/loops/runs`](/reference/loops-api/runs/create-a-run).
* The CLI, using [`truss loops push <base_model>`](/reference/cli/loops/loops-cli#push), which provisions a session, run, and paired sampler in one call.

The minimal HTTP call provisions a run and its paired sampler against an existing session. Replace `2qjl22w` with the `session.id` returned by `POST /v1/loops/sessions`:

```bash theme={"system"}
curl --request POST \
  --url https://api.baseten.co/v1/loops/runs \
  --header "Authorization: Bearer $BASETEN_API_KEY" \
  --header "Content-Type: application/json" \
  --data '{
    "session_id": "2qjl22w",
    "base_model": "Qwen/Qwen3.5-9B"
  }'
```

For the full request body, response shape, and an interactive playground, see [`POST /v1/loops/runs`](/reference/loops-api/runs/create-a-run) in the Loops API reference.

## Request a model

To request a base model that isn't listed, [contact support](mailto:support@baseten.co).
