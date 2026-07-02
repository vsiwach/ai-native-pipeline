# Messages
Source: https://docs.baseten.co/reference/inference-api/messages

reference/inference-api/messages-openapi-spec.json post /v1/messages
Create Anthropic Messages API requests against Baseten Model APIs.

<Note>
  Anthropic Messages API support is in **beta**. Behavior may change before general availability. For production workloads, use the [OpenAI Chat Completions API](/reference/inference-api/chat-completions).
</Note>

<Tip>
  Download the [OpenAPI schema](/reference/inference-api/messages-openapi-spec.json) for code generation and client libraries.
</Tip>

[Model APIs](https://app.baseten.co/model-apis/create) accept requests in the [Anthropic Messages API](https://docs.anthropic.com/en/api/messages) format at `https://inference.baseten.co/v1/messages`.

## Call with the Anthropic SDK

The Anthropic SDK sends the API key as `x-api-key` by default. Baseten reads `Authorization`, so override `default_headers` when creating the client:

<Tabs>
  <Tab title="Python">
    ```python messages.py theme={"system"}
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
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "Hello!"}
        ],
    )

    print(response.content[0].text)
    ```
  </Tab>

  <Tab title="cURL">
    ```bash Request theme={"system"}
    curl https://inference.baseten.co/v1/messages \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -d '{
        "model": "deepseek-ai/DeepSeek-V4-Pro",
        "max_tokens": 1024,
        "messages": [
          {"role": "user", "content": "Hello!"}
        ]
      }'
    ```
  </Tab>
</Tabs>
