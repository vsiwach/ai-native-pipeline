# Function calling
Source: https://docs.baseten.co/inference/function-calling

Tool selection and structured function calls with LLMs

*Function calling* (also called *tool calling*) lets a model choose a tool and produce its arguments from a user request. The model doesn't run the tool itself: your application runs it and can send the result back to the model to produce a final, user-facing response. This fits [chains](/development/chain/overview) and other orchestrators.

<Note>
  Baseten engines including [BIS-LLM](/engines/bis-llm/overview) and [Engine-Builder-LLM](/engines/engine-builder-llm/overview) support function calling, as do [Model APIs](/inference/model-apis/overview) for instant access. Other inference frameworks like [vLLM](/examples/vllm) and [SGLang](/examples/sglang) also support it.
</Note>

## How tool calling works

A typical tool-calling loop looks like:

1. Send the user message and a list of tools.
2. The model returns normal text or one or more tool calls (a name and JSON arguments).
3. Execute the tool calls in your application.
4. Send the tool output back to the model.
5. Receive a final response or additional tool calls.

## Define tools

Tools can be anything: API calls, database queries, or internal scripts.

Docstrings matter. Models use them to decide which tool to call and how to fill parameters:

```python tools.py theme={"system"}
def multiply(a: float, b: float):
    """Multiply two numbers.

    Args:
        a: The first number.
        b: The second number.
    """
    return a * b


def divide(a: float, b: float):
    """Divide two numbers.

    Args:
        a: The dividend.
        b: The divisor (must be non-zero).
    """
    return a / b


def add(a: float, b: float):
    """Add two numbers.

    Args:
        a: The first number.
        b: The second number.
    """
    return a + b


def subtract(a: float, b: float):
    """Subtract two numbers.

    Args:
        a: The number to subtract from.
        b: The number to subtract.
    """
    return a - b
```

### Tool-writing tips

Design small, single-purpose tools and document constraints in docstrings (units, allowed values, required fields). Treat model-provided arguments as untrusted input and validate before execution.

## Serialize functions

Convert functions into JSON-schema tool definitions (OpenAI-compatible format):

```python serialize.py theme={"system"}
from transformers.utils import get_json_schema

calculator_functions = {
    "multiply": multiply,
    "divide": divide,
    "add": add,
    "subtract": subtract,
}

tools = [get_json_schema(f) for f in calculator_functions.values()]
```

## Call the model

Include the `tools` array in your request:

```python call_model.py theme={"system"}
import requests

payload = {
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is 3.14 + 3.14?"},
    ],
    "tools": tools,
    "tool_choice": "auto",  # default
}

MODEL_ID = ""
BASETEN_API_KEY = ""

resp = requests.post(
    f"https://model-{MODEL_ID}.api.baseten.co/production/predict",
    headers={"Authorization": f"Bearer {BASETEN_API_KEY}"},
    json=payload,
)
```

## Control tool selection

Set `tool_choice` to control how the model uses tools. With `auto` (default), the model can respond with text or tool calls. With `required`, the model must return at least one tool call. With `none`, the model returns plain text only. To force a specific tool:

```python tool_choice.py theme={"system"}
"tool_choice": {"type": "function", "function": {"name": "subtract"}}
```

## Parse and execute tool calls

Depending on the engine and model, tool calls are typically returned in an assistant message under `tool_calls`:

```python parse_tool_calls.py theme={"system"}
import json

data = resp.json()
message = data["choices"][0]["message"]

tool_calls = message.get("tool_calls") or []

for tool_call in tool_calls:
    name = tool_call["function"]["name"]
    args = json.loads(tool_call["function"]["arguments"])

    # Validate args in production.
    result = calculator_functions[name](**args)
    print(result)
```

### Full loop: send tool output back for a final answer

If you want the model to turn raw tool output into a user-facing response, append the assistant message and a tool response with the matching `tool_call_id`:

```python full_loop.py theme={"system"}
# Continue the conversation
messages = payload["messages"]
messages.append(message)  # assistant tool call message

# Example: respond to the first tool call
tool_call = tool_calls[0]
name = tool_call["function"]["name"]
args = json.loads(tool_call["function"]["arguments"])
result = calculator_functions[name](**args)

messages.append({
    "role": "tool",
    "tool_call_id": tool_call["id"],
    "content": json.dumps({"result": result}),
})

final_payload = {
    **payload,
    "messages": messages,
}

final_resp = requests.post(
    f"https://model-{MODEL_ID}.api.baseten.co/production/predict",
    headers={"Authorization": f"Bearer {BASETEN_API_KEY}"},
    json=final_payload,
)

print(final_resp.json()["choices"][0]["message"].get("content"))
```

## Practical tips

Use low temperature (0.0-0.3) for reliable tool selection and argument values. Add `enum` and `required` constraints in your JSON schema to guide model outputs. Consider parallel tool calls only if your model supports them. Always validate and sanitize inputs before calling real systems.

## Related

* [Chains](/development/chain/overview): Orchestrate multi-step workflows.
* [Custom engine builder](/engines/engine-builder-llm/custom-engine-builder): Advanced configuration options.
