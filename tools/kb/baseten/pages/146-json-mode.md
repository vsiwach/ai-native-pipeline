# JSON mode
Source: https://docs.baseten.co/inference/json-mode

Constrain model output to syntactically valid JSON

JSON mode forces a model to emit syntactically valid JSON. It's a feature of the OpenAI Chat Completions API, enabled by setting `response_format` to `{"type": "json_object"}`. Use JSON mode when you need parseable JSON but don't need to enforce a specific schema.

For most production use cases, prefer [structured outputs](/inference/structured-outputs). Structured outputs guarantee that the response matches a JSON schema you provide, which is stricter, type-safe, and removes the need to retry or validate after the fact.

## How it works

JSON mode tells the server to constrain the output to valid JSON. You still describe the fields you want in the prompt; the server only enforces well-formedness, not shape.

```python json_mode.py theme={"system"}
import os
from openai import OpenAI

client = OpenAI(
    base_url="https://inference.baseten.co/v1",
    api_key=os.environ["BASETEN_API_KEY"],
)

response = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V4-Pro",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that responds only in JSON."},
        {"role": "user", "content": "List three planets with their distance from the sun in km. Respond as a JSON object with a 'planets' array."},
    ],
    response_format={"type": "json_object"},
)

print(response.choices[0].message.content)
```

Ask for JSON in the prompt so the model produces a useful shape. The server constrains output to valid JSON but doesn't infer the schema from the request.

## JSON mode versus structured outputs

| Feature            | JSON mode                                | Structured outputs                                 |
| ------------------ | ---------------------------------------- | -------------------------------------------------- |
| Output guarantee   | Valid JSON                               | Valid JSON that matches your schema                |
| Schema enforcement | None                                     | Strict (server rejects non-conforming generations) |
| Setup              | Set `response_format` to `json_object`   | Provide a JSON schema or Pydantic model            |
| Best for           | Lightweight extraction, ad hoc responses | Production data extraction, typed pipelines        |

Reach for JSON mode when you don't want to define a schema and the downstream consumer can tolerate flexible field sets. Otherwise, use structured outputs.

## Model support

JSON mode and structured outputs are supported on a per-model basis. See the feature support table on the [Model APIs overview](/inference/model-apis/overview#feature-support) for which models support each.

## Related

* [Structured outputs](/inference/structured-outputs): Schema-enforced JSON output.
* [Model APIs overview](/inference/model-apis/overview): Supported models and feature matrix.
* [Chat Completions reference](/reference/inference-api/chat-completions): Full request and response schema.
