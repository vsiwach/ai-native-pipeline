# Streaming and endpoints
Source: https://docs.baseten.co/development/model/streaming-and-endpoints

Stream model output, expose /v1 HTTP endpoints, and handle raw requests in custom Truss model code.

Clients reach your custom model through the server's HTTP routes. A standard Truss model serves `POST /predict` with arbitrary JSON, and your `predict` method can return a single JSON response or a generator that streams output as it's produced. You can also expose OpenAI- and Anthropic-style `/v1` endpoints by implementing the matching methods, and access the raw request object when you need to customize deserialization or cancel long-running predictions.

## Streaming

Streaming returns results as they're generated instead of waiting for the full response, which cuts wait time for generative models.

* **Faster response time:** Get initial results in under 1 second instead of waiting 10 or more seconds.
* **Improved user experience:** Partial outputs are immediately usable.

To stream, return a generator from `predict` that yields chunks as they're produced. The following sections walk through deploying Falcon 7B with streaming enabled.

### Initialize Truss

Create a new Truss for the model:

```sh Terminal theme={"system"}
truss init falcon-7b && cd falcon-7b
```

### Implement the model without streaming

This first version loads the Falcon 7B model without streaming:

```python model/model.py theme={"system"}
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
from typing import Dict

CHECKPOINT = "tiiuae/falcon-7b-instruct"
DEFAULT_MAX_NEW_TOKENS = 150
DEFAULT_TOP_P = 0.95

class Model:
    def __init__(self, **kwargs) -> None:
        self.tokenizer = None
        self.model = None

    def load(self):
        self.tokenizer = AutoTokenizer.from_pretrained(CHECKPOINT)
        self.model = AutoModelForCausalLM.from_pretrained(
            CHECKPOINT, torch_dtype=torch.bfloat16, trust_remote_code=True, device_map="auto"
        )

    def predict(self, request: Dict) -> Dict:
        prompt = request["prompt"]
        inputs = self.tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True, padding=True)
        input_ids = inputs["input_ids"].to("cuda")
        generation_config = GenerationConfig(temperature=1, top_p=DEFAULT_TOP_P, top_k=40)

        with torch.no_grad():
            return self.model.generate(
                input_ids=input_ids,
                generation_config=generation_config,
                return_dict_in_generate=True,
                output_scores=True,
                pad_token_id=self.tokenizer.eos_token_id,
                max_new_tokens=DEFAULT_MAX_NEW_TOKENS,
            )
```

### Add streaming support

To enable streaming:

* Use `TextIteratorStreamer` to stream tokens as they're generated.
* Run `generate()` in a separate thread to prevent blocking.
* Return a generator that streams results.

```python model/model.py theme={"system"}
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig, TextIteratorStreamer
from threading import Thread
from typing import Dict

CHECKPOINT = "tiiuae/falcon-7b-instruct"

class Model:
    def __init__(self, **kwargs) -> None:
        self.tokenizer = None
        self.model = None

    def load(self):
        self.tokenizer = AutoTokenizer.from_pretrained(CHECKPOINT)
        self.model = AutoModelForCausalLM.from_pretrained(
            CHECKPOINT, torch_dtype=torch.bfloat16, trust_remote_code=True, device_map="auto"
        )

    def predict(self, request: Dict):
        prompt = request["prompt"]
        inputs = self.tokenizer(prompt, return_tensors="pt", max_length=512, truncation=True, padding=True)
        input_ids = inputs["input_ids"].to("cuda")

        streamer = TextIteratorStreamer(self.tokenizer)
        generation_config = GenerationConfig(temperature=1, top_p=0.95, top_k=40)

        def generate():
            self.model.generate(
                input_ids=input_ids,
                generation_config=generation_config,
                return_dict_in_generate=True,
                output_scores=True,
                pad_token_id=self.tokenizer.eos_token_id,
                max_new_tokens=150,
                streamer=streamer,
            )

        thread = Thread(target=generate)
        thread.start()

        def stream_output():
            for text in streamer:
                yield text
            thread.join()

        return stream_output()
```

### Configure `config.yaml`

```yaml config.yaml theme={"system"}
model_name: falcon-streaming
requirements:
  - torch==2.0.1
  - peft==0.4.0
  - scipy==1.11.1
  - sentencepiece==0.1.99
  - accelerate==0.21.0
  - bitsandbytes==0.41.1
  - einops==0.6.1
  - transformers==4.31.0
resources:
  cpu: "4"
  memory: 16Gi
  use_gpu: true
  accelerator: L4
```

### Deploy and invoke

Deploy the model:

```sh Terminal theme={"system"}
truss push --watch
```

Invoke with:

```sh Terminal theme={"system"}
truss predict -d '{"prompt": "Tell me about falcons", "do_sample": true}'
```

## /v1 endpoints

Custom Truss models normally serve `POST /predict` with arbitrary JSON. To also support additional HTTP routes, define the matching methods on your `Model` class. Use these methods when you want custom Python logic but still want clients to call your model through the server's built-in HTTP endpoints.

If you deploy a custom Docker container, Baseten can forward requests to any route exposed by the underlying server. See [Custom Docker containers](/development/model/custom-server).

### Which method to implement

| Method             | Endpoint               | Use it for                                                    |
| ------------------ | ---------------------- | ------------------------------------------------------------- |
| `chat_completions` | `/v1/chat/completions` | Chat-style payloads with a `messages` array.                  |
| `completions`      | `/v1/completions`      | Prompt-style payloads with a `prompt` field.                  |
| `embeddings`       | `/v1/embeddings`       | Embedding requests from text or token inputs.                 |
| `messages`         | `/v1/messages`         | Server-specific message payloads exposed by your deployment.  |
| `responses`        | `/v1/responses`        | Server-specific response payloads exposed by your deployment. |

Implement any subset of these methods, depending on the interface you want to expose.

### API families

| Endpoint               | Family                        |
| ---------------------- | ----------------------------- |
| `/v1/chat/completions` | OpenAI-style chat completions |
| `/v1/completions`      | OpenAI-style text completions |
| `/v1/embeddings`       | OpenAI-style embeddings       |
| `/v1/responses`        | OpenAI-style responses        |
| `/v1/messages`         | Anthropic-style messages      |

This page uses HTTP endpoints as the umbrella term because Truss can expose endpoints from more than one API family.

### chat\_completions

Implement `chat_completions` when your model should accept chat requests.

```python model/model.py theme={"system"}
from typing import Any, Dict

class Model:
    def __init__(self, **kwargs):
        pass

    def load(self):
        pass

    async def predict(self, model_input: Dict[str, Any]):
        return {"output": model_input}

    async def chat_completions(self, model_input: Dict[str, Any], request):
        # Reuse your main inference path so /predict and /v1/chat/completions stay aligned.
        return await self.predict(model_input)
```

The request body follows the chat schema, so `model_input` typically includes fields like:

* `messages`
* `model`
* `stream`
* sampling parameters such as `temperature` and `max_tokens`

If you already have a `predict` method that handles the same payload shape, `chat_completions` can simply delegate to it.

### completions

Implement `completions` when your model should accept prompt-style completion requests.

```python model/model.py theme={"system"}
from typing import Any, Dict

class Model:
    def __init__(self, **kwargs):
        pass

    def load(self):
        pass

    async def completions(self, model_input: Dict[str, Any], request):
        prompt = model_input["prompt"]
        return {
            "id": "cmpl-example",
            "object": "text_completion",
            "choices": [
                {
                    "index": 0,
                    "text": f"You sent: {prompt}",
                    "finish_reason": "stop",
                }
            ],
        }
```

Use `completions` for workloads such as autocomplete, prompt continuation, or fine-tuned models that are designed to extend text instead of following chat-style instructions.

### embeddings, messages, and responses

Implement `embeddings`, `messages`, or `responses` when your deployment should expose those HTTP endpoints from custom model code.

```python model/model.py theme={"system"}
from typing import Any, Dict

class Model:
    def __init__(self, **kwargs):
        pass

    def load(self):
        pass

    def embeddings(self, model_input: Dict[str, Any], request):
        return {"output": "embeddings"}

    def messages(self, model_input: Dict[str, Any], request):
        return {"output": "messages"}

    def responses(self, model_input: Dict[str, Any], request):
        return {"output": "responses"}
```

These methods are forwarded directly to the matching `/v1/*` route, so your implementation can return whatever JSON shape that endpoint expects.

`messages` maps to the Anthropic-style `/v1/messages` route. `embeddings` and `responses` map to OpenAI-style `/v1/embeddings` and `/v1/responses` routes.

### Request and response expectations

* These methods receive the parsed JSON payload as `model_input`.
* If you include a second argument annotated as `fastapi.Request`, you can inspect disconnects or request metadata just like in `predict`. See [Request handling](#request-handling).
* Return JSON that matches the endpoint you expose. Baseten does not automatically convert an arbitrary `predict` response into a different response object for custom model code.

### Endpoint paths

When these methods are defined, your deployment serves the matching HTTP routes in addition to `/predict`.

```text theme={"system"}
/environments/{env}/sync/v1/chat/completions
/environments/{env}/sync/v1/completions
/environments/{env}/sync/v1/embeddings
/environments/{env}/sync/v1/messages
/environments/{env}/sync/v1/responses
```

For production, replace `{env}` with `production`. For development deployments, use `development`.

## Request handling

Truss extracts and validates payloads for you. Access the raw request object when you need to:

* Customize payload deserialization, for example binary protocol buffers.
* Handle disconnections and cancel long-running predictions.

<Tip>You can mix request objects with standard inputs, or use only the request.</Tip>

### Use request objects in Truss

You can define request objects in `preprocess`, `predict`, and `postprocess`:

```python model/model.py theme={"system"}
import fastapi

class Model:
    def preprocess(self, request: fastapi.Request):
        ...

    def predict(self, inputs, request: fastapi.Request):
        ...

    def postprocess(self, inputs, request: fastapi.Request):
        ...
```

### Rules for using requests

* The request must be type-annotated as `fastapi.Request`.
* If you use only the request, Truss skips payload extraction for better performance.
* If you use both the request and standard inputs:
  * The request must be the second argument.
  * Preprocessing transforms the inputs, but the request object stays unchanged.
  * `postprocess` can't take only the request; it must receive the model's output.
  * If `predict` uses only the request, you can't use `preprocess`.

The following example streams output while checking for client disconnects, returning early to cancel the prediction:

```python model/model.py theme={"system"}
import fastapi, asyncio, logging

class Model:
    async def predict(self, inputs, request: fastapi.Request):
        await asyncio.sleep(1)
        if await request.is_disconnected():
            logging.warning("Cancelled before generation.")
            return  # Cancel request on the model engine here.

        for i in range(5):
            await asyncio.sleep(1.0)
            logging.warning(i)
            yield str(i)  # Streaming response
            if await request.is_disconnected():
                logging.warning("Cancelled during generation.")
                return  # Cancel request on the model engine here.
```

<Tip>You must implement request cancellation at the model level, which varies by framework.</Tip>

### Cancel requests in specific frameworks

#### TRT-LLM (polling-based cancellation)

For TensorRT-LLM, use `response_iterator.cancel()` to terminate streaming requests:

```python model/model.py theme={"system"}
async for request_output in response_iterator:
    if await is_cancelled_fn():
        logging.info("Request cancelled. Cancelling Triton request.")
        response_iterator.cancel()
        return
```

<Note>See full example in [TensorRT-LLM Docs](https://developer.nvidia.com/tensorrt-llm).</Note>

#### vLLM (abort API)

For vLLM, use `engine.abort()` to stop processing:

```python model/model.py theme={"system"}
async for request_output in results_generator:
    if await request.is_disconnected():
        await engine.abort(request_id)
        return
```

<Note>See full example in [vLLM Docs](https://docs.vllm.ai/en/latest/dev/engine/async_llm_engine.html#vllm.AsyncLLMEngine.generate).</Note>

### Unsupported request features

* **Streaming file uploads**: Use URLs instead of embedding large data in the request.
* **Client-side headers**: Most headers are stripped; include necessary metadata in the payload.

## Next steps

* [The Model class](/development/model/model-class): Write the `predict`, `chat_completions`, and request-handling methods these endpoints call.
* [Custom Docker servers](/development/model/custom-server): Forward requests to any route your own container exposes.
