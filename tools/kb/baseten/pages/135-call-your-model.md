# Call your model
Source: https://docs.baseten.co/frontier-gateway/calling-your-model

Make your first inference call through Baseten Frontier Gateway with a federated API key issued by your AI lab.

If an AI lab has given you a federated API key for their model, this guide shows you how to call that model through Baseten Frontier Gateway. The gateway is OpenAI-compatible, so any OpenAI SDK or HTTP client works with two changes: the base URL and the auth header.

<Tip>
  The gateway accepts the OpenAI Chat Completions API. If your code already targets OpenAI, point the base URL at Baseten and swap the key. No other changes required.
</Tip>

## Base URL

The default base URL is:

```http theme={"system"}
https://inference.baseten.co/v1
```

If your lab uses a branded domain for the gateway (for example, `https://api.your-lab.com/v1`), use that URL instead. Your lab will tell you which URL to use; the request shape is the same.

## Authentication

Pass your federated API key in the `Authorization` header using the `Api-Key` scheme, **not** `Bearer`:

```http theme={"system"}
Authorization: Api-Key YOUR_API_KEY
```

If your client defaults to `Authorization: Bearer ...`, override it. Federated keys sent as Bearer tokens are rejected.

The key was issued to you by your lab through Baseten's federated key management. You don't manage rotation or limits; those are configured on the lab's side. Treat the key like any other API secret: store it in an environment variable or secret manager, never in source control.

## OpenAI SDK example

Make a chat completion request with the federated key your lab gave you. Replace `YOUR_API_KEY` with that key, and `your-org/your-model` with the model slug your lab gave you.

<Tabs>
  <Tab title="Python">
    Install the OpenAI SDK:

    ```bash theme={"system"}
    pip install openai
    ```

    Make a chat completion request:

    ```python chat.py theme={"system"}
    from openai import OpenAI

    client = OpenAI(
        base_url="https://inference.baseten.co/v1",
        api_key="YOUR_API_KEY",
    )

    response = client.chat.completions.create(
        model="your-org/your-model",
        messages=[{"role": "user", "content": "Hello, world!"}],
    )

    print(response.choices[0].message.content)
    ```
  </Tab>

  <Tab title="JavaScript">
    Install the OpenAI SDK:

    ```bash theme={"system"}
    npm install openai
    ```

    Make a chat completion request:

    ```javascript chat.js theme={"system"}
    import OpenAI from "openai";

    const client = new OpenAI({
        baseURL: "https://inference.baseten.co/v1",
        apiKey: "YOUR_API_KEY",
    });

    const response = await client.chat.completions.create({
        model: "your-org/your-model",
        messages: [{ role: "user", content: "Hello, world!" }],
    });

    console.log(response.choices[0].message.content);
    ```
  </Tab>
</Tabs>

The response follows the standard OpenAI Chat Completions schema:

```json Output theme={"system"}
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "your-org/your-model",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 9,
    "total_tokens": 19
  }
}
```

## curl example

For raw HTTP usage:

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request POST \
    --url https://inference.baseten.co/v1/chat/completions \
    --header "Content-Type: application/json" \
    --header "Authorization: Api-Key YOUR_API_KEY" \
    --data '{
      "model": "your-org/your-model",
      "messages": [
        {"role": "user", "content": "Hello, world!"}
      ]
    }'
  ```

  ```json Output theme={"system"}
  {
    "id": "chatcmpl-...",
    "object": "chat.completion",
    "model": "your-org/your-model",
    "choices": [
      {
        "index": 0,
        "message": {
          "role": "assistant",
          "content": "Hello! How can I help you today?"
        },
        "finish_reason": "stop"
      }
    ],
    "usage": {
      "prompt_tokens": 10,
      "completion_tokens": 9,
      "total_tokens": 19
    }
  }
  ```
</CodeGroup>

## Model slug format

Model slugs are formatted as `your-org/your-model` (for example, `acme/llama-3-70b`). Pass the slug as the `model` parameter on every request. Your lab will tell you which slug or slugs your key has access to; a single key can be authorized for one or more models.

## Streaming, structured outputs, and tool calling

The gateway supports streaming, JSON-schema structured outputs, and tool calling through standard OpenAI parameters (`stream`, `response_format`, `tools`). The configuration and usage patterns are identical to any OpenAI-compatible endpoint:

* For more information on streaming responses, see [Streaming](/inference/streaming).
* For more information on JSON-schema and structured generation, see [Structured outputs](/inference/structured-outputs).
* For more information on tool calling and function definitions, see [Function calling](/inference/function-calling).

## Rate limits

Your federated key has rate and usage limits set by your lab. When a limit is exceeded, the gateway returns `429 Too Many Requests`. For more information on the limit shape, daily reset behavior, and 429 handling, see [Rate and usage limits](/frontier-gateway/rate-limits).

## Run a lab serving a model?

If you're the lab issuing federated keys (rather than a developer consuming them), the [Frontier Gateway overview](/frontier-gateway/overview) covers group and key management, rate limits, and billing webhooks.
