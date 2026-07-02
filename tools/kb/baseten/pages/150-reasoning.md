# Reasoning
Source: https://docs.baseten.co/inference/model-apis/reasoning

Control extended thinking for reasoning-capable models

Some Model APIs support *extended thinking*, where the model reasons through a problem before producing a final answer. The reasoning process generates additional tokens that appear in a separate `reasoning_content` field, distinct from the final response.

## Supported models

| Model           | Slug                                       | Reasoning                           |
| --------------- | ------------------------------------------ | ----------------------------------- |
| DeepSeek V4 Pro | `deepseek-ai/DeepSeek-V4-Pro`              | Enabled by default                  |
| GPT OSS 120B    | `openai/gpt-oss-120b`                      | Enabled by default                  |
| GLM 5.2         | `zai-org/GLM-5.2`                          | Enabled by default                  |
| Kimi K2.5       | `moonshotai/Kimi-K2.5`                     | Opt-in through `chat_template_args` |
| Kimi K2.6       | `moonshotai/Kimi-K2.6`                     | Opt-in through `chat_template_args` |
| Kimi K2.7 Code  | `moonshotai/Kimi-K2.7-Code`                | Opt-in through `chat_template_args` |
| GLM 4.7         | `zai-org/GLM-4.7`                          | Opt-in through `chat_template_args` |
| GLM 5           | `zai-org/GLM-5`                            | Opt-in through `chat_template_args` |
| GLM 5.1         | `zai-org/GLM-5.1`                          | Opt-in through `chat_template_args` |
| Nemotron Super  | `nvidia/Nemotron-120B-A12B`                | Opt-in through `chat_template_args` |
| Nemotron Ultra  | `nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B` | Opt-in through `chat_template_args` |

DeepSeek V4 Pro, GPT OSS 120B, and GLM 5.2 also support [`reasoning_effort`](#control-reasoning-depth).

Models not listed here don't support reasoning.

## Enable thinking

For models marked opt-in in the table above, enable thinking by passing `chat_template_args`.

<Tabs>
  <Tab title="Python">
    Pass `chat_template_args` through `extra_body` since it extends the standard OpenAI API:

    ```python enable_thinking.py theme={"system"}
    response = client.chat.completions.create(
        model="moonshotai/Kimi-K2.5",
        messages=[{"role": "user", "content": "What is the sum of the first 100 prime numbers?"}],
        extra_body={"chat_template_args": {"enable_thinking": True}},
        max_tokens=4096,
        stream=True,
    )
    ```
  </Tab>

  <Tab title="JavaScript">
    Include `chat_template_args` directly in the request options:

    ```javascript enable_thinking.js theme={"system"}
    const response = await client.chat.completions.create({
        model: "moonshotai/Kimi-K2.5",
        messages: [{ role: "user", content: "What is the sum of the first 100 prime numbers?" }],
        chat_template_args: { enable_thinking: true },
        max_tokens: 4096,
        stream: true,
    });
    ```
  </Tab>

  <Tab title="cURL">
    Include `chat_template_args` in the JSON request body:

    ```bash Request theme={"system"}
    curl https://inference.baseten.co/v1/chat/completions \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -d '{
        "model": "moonshotai/Kimi-K2.5",
        "messages": [{"role": "user", "content": "What is the sum of the first 100 prime numbers?"}],
        "chat_template_args": {"enable_thinking": true},
        "max_tokens": 4096,
        "stream": false
      }'
    ```
  </Tab>
</Tabs>

## Control reasoning depth

The `reasoning_effort` parameter controls how thoroughly the model reasons through a problem. DeepSeek V4 Pro, GPT OSS 120B, and GLM 5.2 support this parameter. Supported values vary by model:

| Model           | Supported values                                                     |
| --------------- | -------------------------------------------------------------------- |
| DeepSeek V4 Pro | `none`, `minimal`, `low`, `medium` (default), `high`, `xhigh`, `max` |
| GPT OSS 120B    | `none`, `minimal`, `low`, `medium` (default), `high`, `xhigh`, `max` |
| GLM 5.2         | `none`, `high`, `max`                                                |

Lower values return faster responses with less thorough reasoning; higher values reason longer and cost more output tokens. `none` disables reasoning entirely. GLM 5.2 returns a `400` error for values outside its set.

<Warning>
  A successful request doesn't mean `reasoning_effort` took effect. Models not listed in this table accept the parameter but ignore it.
</Warning>

<Tabs>
  <Tab title="DeepSeek V4 Pro">
    <Tabs>
      <Tab title="Python">
        Pass `reasoning_effort` through `extra_body` since it extends the standard OpenAI API:

        ```python reasoning_effort.py theme={"system"}
        from openai import OpenAI
        import os

        client = OpenAI(
            base_url="https://inference.baseten.co/v1",
            api_key=os.environ.get("BASETEN_API_KEY")
        )

        response = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V4-Pro",
            messages=[
                {"role": "user", "content": "What is the sum of the first 100 prime numbers?"}
            ],
            extra_body={"reasoning_effort": "high"}  # [!code ++]
        )

        print(response.choices[0].message.content)
        ```
      </Tab>

      <Tab title="JavaScript">
        Include `reasoning_effort` directly in the request options:

        ```javascript reasoning_effort.js theme={"system"}
        import OpenAI from "openai";

        const client = new OpenAI({
            baseURL: "https://inference.baseten.co/v1",
            apiKey: process.env.BASETEN_API_KEY,
        });

        const response = await client.chat.completions.create({
            model: "deepseek-ai/DeepSeek-V4-Pro",
            messages: [
                { role: "user", content: "What is the sum of the first 100 prime numbers?" }
            ],
            reasoning_effort: "high"  // [!code ++]
        });

        console.log(response.choices[0].message.content);
        ```
      </Tab>

      <Tab title="cURL">
        Include `reasoning_effort` in the JSON request body:

        ```bash Request theme={"system"}
        curl https://inference.baseten.co/v1/chat/completions \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer $BASETEN_API_KEY" \
          -d '{
            "model": "deepseek-ai/DeepSeek-V4-Pro",
            "messages": [{"role": "user", "content": "What is the sum of the first 100 prime numbers?"}],
            "reasoning_effort": "high"
          }'
        ```
      </Tab>
    </Tabs>
  </Tab>

  <Tab title="GPT OSS 120B">
    <Tabs>
      <Tab title="Python">
        Pass `reasoning_effort` through `extra_body` since it extends the standard OpenAI API:

        ```python reasoning_effort.py theme={"system"}
        from openai import OpenAI
        import os

        client = OpenAI(
            base_url="https://inference.baseten.co/v1",
            api_key=os.environ.get("BASETEN_API_KEY")
        )

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "user", "content": "What is the sum of the first 100 prime numbers?"}
            ],
            extra_body={"reasoning_effort": "high"}  # [!code ++]
        )

        print(response.choices[0].message.content)
        ```
      </Tab>

      <Tab title="JavaScript">
        Include `reasoning_effort` directly in the request options:

        ```javascript reasoning_effort.js theme={"system"}
        import OpenAI from "openai";

        const client = new OpenAI({
            baseURL: "https://inference.baseten.co/v1",
            apiKey: process.env.BASETEN_API_KEY,
        });

        const response = await client.chat.completions.create({
            model: "openai/gpt-oss-120b",
            messages: [
                { role: "user", content: "What is the sum of the first 100 prime numbers?" }
            ],
            reasoning_effort: "high"  // [!code ++]
        });

        console.log(response.choices[0].message.content);
        ```
      </Tab>

      <Tab title="cURL">
        Include `reasoning_effort` in the JSON request body:

        ```bash Request theme={"system"}
        curl https://inference.baseten.co/v1/chat/completions \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer $BASETEN_API_KEY" \
          -d '{
            "model": "openai/gpt-oss-120b",
            "messages": [{"role": "user", "content": "What is the sum of the first 100 prime numbers?"}],
            "reasoning_effort": "high"
          }'
        ```
      </Tab>
    </Tabs>
  </Tab>

  <Tab title="GLM 5.2">
    <Tabs>
      <Tab title="Python">
        Pass `reasoning_effort` through `extra_body` since it extends the standard OpenAI API:

        ```python reasoning_effort.py theme={"system"}
        from openai import OpenAI
        import os

        client = OpenAI(
            base_url="https://inference.baseten.co/v1",
            api_key=os.environ.get("BASETEN_API_KEY")
        )

        response = client.chat.completions.create(
            model="zai-org/GLM-5.2",
            messages=[
                {"role": "user", "content": "What is the sum of the first 100 prime numbers?"}
            ],
            extra_body={"reasoning_effort": "high"}  # [!code ++]
        )

        print(response.choices[0].message.content)
        ```
      </Tab>

      <Tab title="JavaScript">
        Include `reasoning_effort` directly in the request options:

        ```javascript reasoning_effort.js theme={"system"}
        import OpenAI from "openai";

        const client = new OpenAI({
            baseURL: "https://inference.baseten.co/v1",
            apiKey: process.env.BASETEN_API_KEY,
        });

        const response = await client.chat.completions.create({
            model: "zai-org/GLM-5.2",
            messages: [
                { role: "user", content: "What is the sum of the first 100 prime numbers?" }
            ],
            reasoning_effort: "high"  // [!code ++]
        });

        console.log(response.choices[0].message.content);
        ```
      </Tab>

      <Tab title="cURL">
        Include `reasoning_effort` in the JSON request body:

        ```bash Request theme={"system"}
        curl https://inference.baseten.co/v1/chat/completions \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer $BASETEN_API_KEY" \
          -d '{
            "model": "zai-org/GLM-5.2",
            "messages": [{"role": "user", "content": "What is the sum of the first 100 prime numbers?"}],
            "reasoning_effort": "high"
          }'
        ```
      </Tab>
    </Tabs>
  </Tab>
</Tabs>

Reasoning improves quality for tasks that benefit from step-by-step thinking: mathematical calculations, multi-step logic problems, code generation with complex requirements, and analysis requiring multiple considerations.

For straightforward tasks like simple Q\&A or text generation, reasoning adds latency and token cost without improving quality. In these cases, use a model without reasoning support or set `reasoning_effort` to `low`.

### Parse the response

The model's thinking process appears in `reasoning_content`, separate from the final answer in `content`. Both fields are returned on the message object.

<Tabs>
  <Tab title="Python">
    Read `reasoning_content` and `content` directly off the message object:

    ```python parse_reasoning.py theme={"system"}
    from openai import OpenAI
    import os

    client = OpenAI(
        base_url="https://inference.baseten.co/v1",
        api_key=os.environ.get("BASETEN_API_KEY"),
    )

    response = client.chat.completions.create(
        model="moonshotai/Kimi-K2.6",
        messages=[{"role": "user", "content": "Is 91 a prime number? Answer in one sentence."}],
        extra_body={"chat_template_args": {"enable_thinking": True}},
    )

    message = response.choices[0].message
    print("Reasoning:", message.reasoning_content)
    print("Answer:", message.content)
    ```
  </Tab>

  <Tab title="JavaScript">
    Read `reasoning_content` and `content` from the returned message:

    ```javascript parse_reasoning.js theme={"system"}
    import OpenAI from "openai";

    const client = new OpenAI({
        baseURL: "https://inference.baseten.co/v1",
        apiKey: process.env.BASETEN_API_KEY,
    });

    const response = await client.chat.completions.create({
        model: "moonshotai/Kimi-K2.6",
        messages: [{ role: "user", content: "Is 91 a prime number? Answer in one sentence." }],
        chat_template_args: { enable_thinking: true },
    });

    const message = response.choices[0].message;
    console.log("Reasoning:", message.reasoning_content);
    console.log("Answer:", message.content);
    ```
  </Tab>

  <Tab title="cURL">
    Pipe the response through `jq` to extract each field:

    ```bash Request theme={"system"}
    curl https://inference.baseten.co/v1/chat/completions \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -d '{
        "model": "moonshotai/Kimi-K2.6",
        "messages": [{"role": "user", "content": "Is 91 a prime number? Answer in one sentence."}],
        "chat_template_args": {"enable_thinking": true}
      }' | jq '.choices[0].message | {reasoning: .reasoning_content, answer: .content}'
    ```
  </Tab>
</Tabs>

The response body contains both fields on the assistant message:

```json Response theme={"system"}
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "reasoning_content": "The user is asking whether 91 is a prime number... 91 = 7 × 13, so it is not prime...",
        "content": "No, 91 is not a prime number because it can be factored as $7 \\times 13$."
      }
    }
  ],
  "usage": {
    "prompt_tokens": 21,
    "completion_tokens": 203,
    "total_tokens": 224
  }
}
```

Reasoning tokens are included in `completion_tokens` and count toward your total usage and billing.

## Next steps

<CardGroup>
  <Card title="Model APIs overview" icon="layer-group" href="/inference/model-apis/overview">
    Supported models, pricing, and the feature support matrix
  </Card>

  <Card title="Structured outputs" icon="brackets-curly" href="/inference/structured-outputs">
    Constrain reasoning models to a JSON schema
  </Card>
</CardGroup>
