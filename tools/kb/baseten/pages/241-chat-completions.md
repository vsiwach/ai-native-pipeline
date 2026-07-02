# Chat Completions
Source: https://docs.baseten.co/reference/inference-api/chat-completions

reference/inference-api/llm-openapi-spec.json post /v1/chat/completions
Create chat completions using Baseten Model APIs, an OpenAI-compatible endpoint for managed LLMs.

<Tip>
  Download the [OpenAPI schema](/reference/inference-api/llm-openapi-spec.json) for code generation and client libraries.
</Tip>

[Model APIs](https://app.baseten.co/model-apis/create) provide instant access to high-performance open-source LLMs through an OpenAI-compatible endpoint.

## Replace OpenAI with Baseten

Switching from OpenAI to Baseten takes two changes: the base URL and API key.

<Tabs>
  <Tab title="Python">
    To switch to Baseten with the Python SDK, change `base_url` and `api_key` when initializing the client:

    ```python chat_completions.py theme={"system"}
    from openai import OpenAI
    import os

    client = OpenAI(
        base_url="https://inference.baseten.co/v1",
        api_key=os.environ["BASETEN_API_KEY"],
    )

    response = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V4-Pro",
        messages=[{"role": "user", "content": "Hello!"}],
    )
    ```
  </Tab>

  <Tab title="JavaScript">
    To switch to Baseten with the JavaScript SDK, change `baseURL` and `apiKey` when initializing the client:

    ```javascript chat_completions.js theme={"system"}
    import OpenAI from "openai";

    const client = new OpenAI({
        baseURL: "https://inference.baseten.co/v1",
        apiKey: process.env.BASETEN_API_KEY,
    });

    const response = await client.chat.completions.create({
        model: "deepseek-ai/DeepSeek-V4-Pro",
        messages: [{ role: "user", content: "Hello!" }],
    });
    ```
  </Tab>

  <Tab title="cURL">
    To call Baseten with cURL, send a POST request to `inference.baseten.co` with your API key:

    ```bash Request theme={"system"}
    curl https://inference.baseten.co/v1/chat/completions \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -d '{
        "model": "deepseek-ai/DeepSeek-V4-Pro",
        "messages": [{"role": "user", "content": "Hello!"}]
      }'
    ```
  </Tab>
</Tabs>

Deploy a [Model API](https://app.baseten.co/model-apis/create) to get started.

<Info>
  For detailed usage guides including structured outputs and tool calling, see [Using Model APIs](/inference/model-apis/overview).
</Info>

<Note>
  OpenAI-compatible models you deploy yourself also support the chat completions format at their own base URL: `https://model-{model_id}.api.baseten.co/v1/chat/completions`. See [deployed model endpoints](/reference/inference-api/overview#deployed-model-endpoints) for URL formats.
</Note>
