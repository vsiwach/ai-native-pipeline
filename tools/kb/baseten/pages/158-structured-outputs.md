# Structured outputs
Source: https://docs.baseten.co/inference/structured-outputs

JSON schema validation and controlled text generation across all engines

Structured outputs let you generate text that conforms to specific JSON schemas, providing reliable data extraction and controlled text generation. [Model APIs](/inference/model-apis/overview) support structured outputs. For self-deployed models, Baseten engines like [BIS-LLM](/engines/bis-llm/overview) and [Engine-Builder-LLM](/engines/engine-builder-llm/overview) support them, as do other inference frameworks like [vLLM](/examples/vllm) and [SGLang](/examples/sglang).

## Quick start

Structured outputs require two components: a Pydantic schema defining your expected output format, and an API call that enforces that schema.

### Define a schema

Define a Pydantic model whose fields describe the output you want:

```python schema.py theme={"system"}
from pydantic import BaseModel

class Task(BaseModel):
    title: str
    priority: str  # "low", "medium", "high"
    due_date: str
    description: str
```

Each field requires a type annotation. The model's response will conform to these types exactly.

### Generate structured output

Pass the schema to the parse method and read the typed result:

```python structured_output.py theme={"system"}
import os
from pydantic import BaseModel
from openai import OpenAI

class Task(BaseModel):
    title: str
    priority: str
    due_date: str
    description: str

client = OpenAI(
    api_key=os.environ['BASETEN_API_KEY'],
    base_url="https://model-xxxxxx.api.baseten.co/environments/production/sync/v1"
)

response = client.beta.chat.completions.parse(
    model="not-required",
    messages=[
        {"role": "user", "content": "Create a task for: Review the quarterly report by next Friday"}
    ],
    response_format=Task
)

task = response.choices[0].message.parsed
print(f"Task: {task.title}")
print(f"Priority: {task.priority}")
```

Point `base_url` to your model's production endpoint. Pass your Pydantic class to `response_format` and use `beta.chat.completions.parse` instead of the regular `create` method.

The response includes a `parsed` attribute with your data already converted to a `Task` object, so no JSON parsing is needed.

## Engine support

Structured outputs are compatible with:

* **Engine-Builder-LLM**, except when Lookahead speculative decoding is configured.
* **BIS-LLM**, except in some configurations, such as when the overlap scheduler is enabled.

### Model support

All Engine-Builder-LLM and BIS-LLM models support structured outputs with no extra configuration.

## Best practices

### Schema design

* **Keep schemas simple**: two to three levels of nesting for best results.
* **Use basic types**: str, int, float, bool when possible.
* **Set defaults**: Provide reasonable default values for optional fields.
* **Descriptive names**: Use clear, descriptive field names.

### Prompt engineering

* **Low temperature**: Use 0.1 to 0.3 for consistent outputs.
* **Provide schema**: Dump the model schema and few-shot examples into context.
* **Provide context**: Give background for complex schemas.

## Related

* [Engine-Builder-LLM overview](/engines/engine-builder-llm/overview): Dense model documentation.
* [BIS-LLM overview](/engines/bis-llm/overview): MoE model documentation.
* [Quantization guide](/engines/performance-concepts/quantization-guide): `FP8`/`FP4` trade-offs.
