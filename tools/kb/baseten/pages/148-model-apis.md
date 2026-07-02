# Model APIs
Source: https://docs.baseten.co/inference/model-apis/overview

OpenAI-compatible endpoints for high-performance LLMs

Model APIs provide instant access to high-performance LLMs through endpoints that are compatible with both the [OpenAI Chat Completions API](/reference/inference-api/chat-completions) and the [Anthropic Messages API](/reference/inference-api/messages) (beta). Point your existing OpenAI or Anthropic SDK at Baseten's inference endpoint and start making calls, no model deployment required.

Unlike [dedicated deployments](/development/model/build-your-first-model), where you'd configure hardware, engines, and scaling yourself, Model APIs run on shared infrastructure that Baseten manages. You get a fixed set of popular models with optimized serving out of the box. When you need a model that isn't in the supported list, or want dedicated GPUs with custom scaling, deploy your own with [Truss](/development/model/overview).

## Supported models

[Run inference](#run-inference) against any Model API to get started.

<Note>
  Context and output limits reflect Baseten's live serving configuration, which can differ from a model's advertised native maximum. We extend limits as they meet our performance bar; this table and [`/v1/models`](#list-available-models) always reflect what's currently served.
</Note>

<SupportedModelsTable />

## Pricing

Model APIs bill per million tokens. For current per-model rates, see the [Model APIs pricing page](https://www.baseten.co/pricing).

Cached input tokens are prompt tokens served from the KV cache, billed at a discounted rate. Every request participates in caching automatically, with no flags or opt-in steps.

## Feature support

All models support [tool calling](/inference/function-calling) (also known as function calling), [structured outputs](/inference/structured-outputs), and [JSON mode](/inference/json-mode). See the table below for per-model coverage of reasoning and vision. For reasoning-specific configuration, see [Reasoning](/inference/model-apis/reasoning). For image and video inputs, see [Vision](/inference/model-apis/vision).

<FeatureSupportTable />

<Note>GLM models, Nemotron Super, and Nemotron Ultra also support `top_p` and `top_k` sampling parameters.</Note>

## Run inference

Model APIs support both OpenAI's Chat Completions and Anthropic's Messages APIs. Set your base URL, API key, and [model name](#supported-models) to start making requests.

### Use the OpenAI SDK

Call supported models using the [OpenAI Chat Completions API](/reference/inference-api/chat-completions) at `https://inference.baseten.co/v1/chat/completions`.

<Tabs>
  <Tab title="Python">
    ```python chat_completions.py theme={"system"}
    from openai import OpenAI
    import os

    client = OpenAI(
        base_url="https://inference.baseten.co/v1",
        api_key=os.environ["BASETEN_API_KEY"],
    )

    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V4-Pro",
        messages=[
            {"role": "system", "content": "You are a concise technical writer."},
            {"role": "user", "content": "What is gradient descent?"},
            {"role": "assistant", "content": "An optimization algorithm that iteratively adjusts model parameters by moving in the direction of steepest decrease in the loss function."},
            {"role": "user", "content": "How does the learning rate affect it?"}
        ],
    )

    print(response.choices[0].message.content)
    ```
  </Tab>

  <Tab title="JavaScript">
    ```javascript chat_completions.js theme={"system"}
    import OpenAI from "openai";

    const client = new OpenAI({
        baseURL: "https://inference.baseten.co/v1",
        apiKey: process.env.BASETEN_API_KEY,
    });

    const response = await client.chat.completions.create({
        model: "deepseek-ai/DeepSeek-V4-Pro",
        messages: [
            { role: "system", content: "You are a concise technical writer." },
            { role: "user", content: "What is gradient descent?" },
            { role: "assistant", content: "An optimization algorithm that iteratively adjusts model parameters by moving in the direction of steepest decrease in the loss function." },
            { role: "user", content: "How does the learning rate affect it?" }
        ],
    });

    console.log(response.choices[0].message.content);
    ```
  </Tab>

  <Tab title="cURL">
    ```bash Request theme={"system"}
    curl https://inference.baseten.co/v1/chat/completions \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -d '{
        "model": "deepseek-ai/DeepSeek-V4-Pro",
        "messages": [
          {"role": "system", "content": "You are a concise technical writer."},
          {"role": "user", "content": "What is gradient descent?"},
          {"role": "assistant", "content": "An optimization algorithm that iteratively adjusts model parameters by moving in the direction of steepest decrease in the loss function."},
          {"role": "user", "content": "How does the learning rate affect it?"}
        ]
      }'
    ```
  </Tab>
</Tabs>

Replace the model slug with any model from the supported models table.

### Use the Anthropic SDK

Call supported models using the [Anthropic Messages API](/reference/inference-api/messages) at `https://inference.baseten.co/v1/messages`.

<Note>
  Anthropic Messages API support is in **beta**. Behavior may change before general availability. For production workloads, use the [OpenAI Chat Completions API](/reference/inference-api/chat-completions).
</Note>

<Tabs>
  <Tab title="Python">
    ```python messages_api.py theme={"system"}
    import anthropic
    import os

    API_KEY = os.environ["BASETEN_API_KEY"]

    client = anthropic.Anthropic(
        base_url="https://inference.baseten.co",
        api_key=API_KEY,
        default_headers={"Authorization": f"Bearer {API_KEY}"},
    )

    response = client.messages.create(
        model="deepseek-ai/DeepSeek-V4-Pro",
        max_tokens=4096,
        system="You are a concise technical writer.",
        messages=[
            {"role": "user", "content": "What is gradient descent?"},
            {"role": "assistant", "content": "An optimization algorithm that iteratively adjusts model parameters by moving in the direction of steepest decrease in the loss function."},
            {"role": "user", "content": "How does the learning rate affect it?"}
        ],
    )

    for block in response.content:
        if block.type == "text":
            print(block.text)
    ```
  </Tab>

  <Tab title="JavaScript">
    ```javascript messages_api.js theme={"system"}
    import Anthropic from "@anthropic-ai/sdk";

    const apiKey = process.env.BASETEN_API_KEY;

    const client = new Anthropic({
        baseURL: "https://inference.baseten.co",
        apiKey: apiKey,
        defaultHeaders: { Authorization: `Bearer ${apiKey}` },
    });

    const response = await client.messages.create({
        model: "deepseek-ai/DeepSeek-V4-Pro",
        max_tokens: 4096,
        system: "You are a concise technical writer.",
        messages: [
            { role: "user", content: "What is gradient descent?" },
            { role: "assistant", content: "An optimization algorithm that iteratively adjusts model parameters by moving in the direction of steepest decrease in the loss function." },
            { role: "user", content: "How does the learning rate affect it?" }
        ],
    });

    for (const block of response.content) {
        if (block.type === "text") console.log(block.text);
    }
    ```
  </Tab>

  <Tab title="cURL">
    ```bash Request theme={"system"}
    curl https://inference.baseten.co/v1/messages \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -d '{
        "model": "deepseek-ai/DeepSeek-V4-Pro",
        "max_tokens": 4096,
        "system": "You are a concise technical writer.",
        "messages": [
          {"role": "user", "content": "What is gradient descent?"},
          {"role": "assistant", "content": "An optimization algorithm that iteratively adjusts model parameters by moving in the direction of steepest decrease in the loss function."},
          {"role": "user", "content": "How does the learning rate affect it?"}
        ]
      }'
    ```
  </Tab>
</Tabs>

The Anthropic SDK sends the API key as `x-api-key` by default. Baseten reads `Authorization`, so override `default_headers` as shown.

## List available models

Query the `/v1/models` endpoint for the current list of models with metadata including pricing, context lengths, and supported features:

```bash Request theme={"system"}
curl https://inference.baseten.co/v1/models \
  -H "Authorization: Bearer $BASETEN_API_KEY"
```

## Migrate

To migrate to Baseten, change the base URL, API key, and model name.

<Tabs>
  <Tab title="OpenAI SDK">
    1. Replace your OpenAI API key with a [Baseten API key](https://app.baseten.co/settings/api_keys).
    2. Change the base URL to `https://inference.baseten.co/v1`.
    3. Update the model name to a Baseten model slug.

    ```python migrate.py theme={"system"}
    from openai import OpenAI
    import os

    client = OpenAI(
        base_url="https://inference.baseten.co/v1",  # [!code ++]
        api_key=os.environ["BASETEN_API_KEY"]  # [!code ++]
    )

    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V4-Pro",  # [!code ++]
        messages=[{"role": "user", "content": "Hello"}]
    )
    ```
  </Tab>

  <Tab title="Anthropic SDK">
    1. Replace your Anthropic API key with a [Baseten API key](https://app.baseten.co/settings/api_keys).
    2. Change the base URL to `https://inference.baseten.co`.
    3. Override `default_headers` so the SDK sends `Authorization` instead of `x-api-key`.
    4. Update the model name to a [supported Baseten model slug](#supported-models).

    ```python migrate.py theme={"system"}
    import anthropic
    import os

    API_KEY = os.environ["BASETEN_API_KEY"]

    client = anthropic.Anthropic(
        base_url="https://inference.baseten.co",  # [!code ++]
        api_key=API_KEY,  # [!code ++]
        default_headers={"Authorization": f"Bearer {API_KEY}"},  # [!code ++]
    )

    response = client.messages.create(
        model="deepseek-ai/DeepSeek-V4-Pro",  # [!code ++]
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hello"}]
    )
    ```
  </Tab>
</Tabs>

## Handle errors

Model APIs return standard HTTP error codes:

| Code | Meaning                                 |
| ---- | --------------------------------------- |
| 400  | Invalid request (check your parameters) |
| 401  | Invalid or missing API key              |
| 402  | Payment required                        |
| 404  | Model not found                         |
| 429  | Rate limit exceeded                     |
| 500  | Internal server error                   |

Each error response includes a JSON body with details about the issue and suggested resolutions.

## Next steps

<CardGroup>
  <Card title="Reasoning" icon="brain" href="/inference/model-apis/reasoning">
    Control extended thinking for complex tasks
  </Card>

  <Card title="Vision" icon="image" href="/inference/model-apis/vision">
    Send images and videos alongside text
  </Card>

  <Card title="Rate limits" icon="gauge" href="/inference/model-apis/rate-limits-and-budgets">
    Understand and configure rate limits
  </Card>

  <Card title="API reference" icon="code" href="/reference/inference-api/chat-completions">
    Complete parameter documentation
  </Card>
</CardGroup>
