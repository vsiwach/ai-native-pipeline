# Call your model
Source: https://docs.baseten.co/inference/calling-your-model

Run inference on deployed models

This page covers calling self-deployed models with your workspace API key. For hosted open-source models with no deployment step, see [Model APIs](/inference/model-apis/overview).

Once deployed, your model is accessible through an [API endpoint](/reference/inference-api/overview). To make an inference request, you'll need:

* **Model ID**: Found in the Baseten dashboard or returned when you deploy.
* **[API key](/organization/api-keys)**: Authenticates your requests.
* **JSON-serializable model input**: The data your model expects.

<Warning>
  We recommend server-side calls to your model. Client-side code may expose your Baseten API key.
  Dedicated deployment endpoints don't currently include CORS response headers, so browser-based calls may be blocked.
</Warning>

## Authentication

Include your API key in the `Authorization` header:

```bash Request theme={"system"}
curl -X POST https://model-YOUR_MODEL_ID.api.baseten.co/environments/production/predict \
  -H "Authorization: Bearer $BASETEN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, world!"}'
```

In Python with requests:

```python predict.py theme={"system"}
import requests
import os

api_key = os.environ["BASETEN_API_KEY"]
model_id = "YOUR_MODEL_ID"

response = requests.post(
    f"https://model-{model_id}.api.baseten.co/environments/production/predict",
    headers={"Authorization": f"Bearer {api_key}"},
    json={"prompt": "Hello, world!"},
)

print(response.json())
```

<Note>
  Baseten also accepts the legacy `Authorization: Api-Key <api_key>` scheme on every endpoint, so existing scripts continue to work:

  ```bash Request theme={"system"}
  curl -X POST https://model-YOUR_MODEL_ID.api.baseten.co/environments/production/predict \
    -H "Authorization: Api-Key $BASETEN_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Hello, world!"}'
  ```
</Note>

## Predict API endpoints

Baseten provides multiple endpoints for different inference modes:

* [`/predict`](/reference/inference-api/overview#predict-endpoints): Standard synchronous inference.
* [`/async_predict`](/reference/inference-api/overview#predict-endpoints): Asynchronous inference for long-running tasks.

Endpoints are available for environments and all deployments. See the [API reference](/reference/inference-api/overview) for details.

## Sync API endpoints

Custom servers support both `predict` endpoints and a special `sync` endpoint. Use the `sync` endpoint to call different routes in your custom server:

```text URL theme={"system"}
https://model-{model-id}.api.baseten.co/environments/{production}/sync/{route}
```

These examples show how the sync endpoint maps to the custom server's routes:

* `https://model-{model_id}.../sync/health` -> `/health`
* `https://model-{model_id}.../sync/items` -> `/items`
* `https://model-{model_id}.../sync/items/123` -> `/items/123`

## OpenAI SDK

When you deploy a model with Engine-Builder, you'll get an OpenAI-compatible server. If you already use one of the OpenAI SDKs, update the base URL to your Baseten model URL and include your Baseten API key:

```python openai_client.py theme={"system"}
import os
from openai import OpenAI

model_id = "abcdef" # TODO: replace with your model id
api_key = os.environ.get("BASETEN_API_KEY")
model_url = f"https://model-{model_id}.api.baseten.co/environments/production/sync/v1"

client = OpenAI(
    base_url=model_url,
    api_key=api_key,
)

stream = client.chat.completions.create(
    model="Qwen/Qwen2.5-3B-Instruct",  # must match --served-model-name in the deployment
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ],
    stream=True,
)

for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        print(chunk.choices[0].delta.content, end="")
```

## External LLM gateways

Any LLM gateway that speaks the OpenAI protocol, such as LiteLLM or OpenRouter, can route traffic to a Baseten deployment. Configure the gateway with three values:

* **Base URL**: `https://model-{model_id}.api.baseten.co/environments/production/sync/v1`, using the model ID for your deployment. Click **API endpoint** on the model page in the Baseten dashboard to copy the full URL.
* **Model name**: The value of `--served-model-name` from your deployment's `start_command`. See the [vLLM example](/examples/vllm) for where this is set. When a single gateway routes to several deployments, use an `org/model` naming convention (for example, `acme/llama-3-70b`) to keep routing unambiguous.
* **API key**: A [Baseten API key](/organization/api-keys) with access to the deployment.

The gateway sends requests to `{base_url}/chat/completions` with `model` set to the served model name and an `Authorization: Bearer <key>` header.

## Alternative invocation methods

* **Baseten CLI**: [`baseten model predict`](/reference/cli/baseten/model)
* **Model Dashboard**: "Playground" button in the Baseten UI
