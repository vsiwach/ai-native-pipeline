# Custom engine builder
Source: https://docs.baseten.co/engines/engine-builder-llm/custom-engine-builder

Implement custom model.py for business logic, logging, and advanced inference patterns

Implement custom business logic, request handling, and inference patterns in `model.py` while maintaining TensorRT-LLM performance. Custom engine builder enables billing integration, request tracing, fan-out generation, and multi-response workflows.

## Overview

The custom engine builder lets you:

* **Implement business logic**: Billing, usage tracking, access control.
* **Add custom logging**: Request tracing, performance monitoring, audit trails.
* **Create advanced inference patterns**: Fan-out generation, custom chat templates.
* **Integrate external services**: APIs, databases, monitoring systems.
* **Optimize performance**: Concurrent processing, custom batching strategies.

## When to use custom engine builder

### Ideal use cases

**Business logic integration:**

* **Usage tracking**: Monitor token usage per customer/request.
* **Access control**: Implement custom authentication/authorization.
* **Rate limiting**: Custom rate limiting based on user tiers.
* **Audit logging**: Compliance and security requirements.

**Advanced inference patterns:**

* **Fan-out generation**: Generate multiple responses from one request.
* **Custom chat templates**: Domain-specific conversation formats.
* **Multi-response workflows**: Parallel processing of variations.
* **Conditional generation**: Business rule-based output modification.

**Performance and monitoring:**

* **Custom logging**: Request tracing, performance metrics.
* **Concurrent processing**: Parallel generation for improved throughput.
* **Usage analytics**: Track patterns and optimize accordingly.
* **Error handling**: Custom error responses and fallback logic.

## Implementation

### Fan-out generation example

Multi-generation fan-out generates multiple texts from a single request. Running them sequentially ensures the KV cache is created before subsequent generations.

```python model/model.py theme={"system"}
# model/model.py
import copy
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, Request
from starlette.responses import JSONResponse, StreamingResponse

Message = Dict[str, str]  # {"role": "...", "content": "..."}

class Model:
    def __init__(self, trt_llm, **kwargs) -> None:
        self._secrets = kwargs["secrets"]
        self._engine = trt_llm["engine"]

    async def predict(self, model_input: Dict[str, Any], request: Request) -> Any:
        # Validate request structure
        if not isinstance(model_input, dict):
            raise HTTPException(status_code=400, detail="Request body must be a JSON object.")

        # Enforce non-streaming for this example
        if bool(model_input.get("stream", False)):
            raise HTTPException(status_code=400, detail="stream=true is not supported here; set stream=false.")

        # Extract base messages and fan-out tasks
        prompt_key, base_messages = self._get_base_messages(model_input)
        n, suffix_tasks = self._parse_fanout(model_input)

        # Build reusable request (don't forward fan-out params to engine)
        base_req = copy.deepcopy(model_input)
        base_req.pop("suffix_messages", None)
        
        # Extract debug ID for logging/tracing
        debug_id = request.headers.get("X-Debug-ID", "")

        # Run sequential generations
        per_gen_payloads: List[Any] = []

        async def run_generation(i: int) -> Any:
            msgs_i = copy.deepcopy(base_messages)
            if suffix_tasks is not None:
                msgs_i.extend(suffix_tasks[i])
            base_req[prompt_key] = msgs_i
            
            # Debug logging
            if debug_id:
                print(f"Running generation {debug_id} {i} with messages: {msgs_i}")
            
            # Time the generation
            start_time = asyncio.get_event_loop().time()
            resp = await self._engine.chat_completions(request=request, model_input=base_req)
            end_time = asyncio.get_event_loop().time()
            
            # Debug logging
            if debug_id:
                duration = end_time - start_time
                print(f"Result Generation {debug_id} {i} response: {resp} (took {duration:.3f}s)")
            
            # Validate response type
            if isinstance(resp, StreamingResponse) or hasattr(resp, "body_iterator"):
                raise HTTPException(status_code=400, detail="Engine returned streaming but stream=false was requested.")

            return resp

        # Run first generation
        payload = await run_generation(0)
        per_gen_payloads.append(payload)
        
        # Run remaining generations concurrently
        if n > 1:
            results = await asyncio.gather(*(run_generation(i) for i in range(1, n)))
            per_gen_payloads.extend(results)

        # Convert to OpenAI-ish multi-choice response
        out = self._to_openai_choices(per_gen_payloads)
        return JSONResponse(content=out.model_dump())

    # Helper methods
    def _get_base_messages(self, model_input: Dict[str, Any]) -> Tuple[str, List[Message]]:
        """Extract and validate base messages from request."""
        if "prompt" in model_input:
            raise HTTPException(status_code=400, detail='Use "messages" instead of "prompt" for chat models.')
        if "messages" not in model_input:
            raise HTTPException(status_code=400, detail='Request must include "messages" field.')
        
        key = "messages"
        msgs = model_input.get(key)
        if not isinstance(msgs, list):
            raise HTTPException(status_code=400, detail=f'"{key}" must be a list of messages.')

        for m in msgs:
            if not isinstance(m, dict) or "role" not in m or "content" not in m:
                raise HTTPException(status_code=400, detail=f'Each item in "{key}" must have role+content.')
        
        return key, msgs

    def _parse_fanout(self, model_input: Dict[str, Any]) -> Tuple[int, Optional[List[List[Message]]]]:
        """Parse and validate fan-out configuration."""
        suffix = model_input.get("suffix_messages", None)

        if not isinstance(suffix, list) or any(not isinstance(t, list) for t in suffix):
            raise HTTPException(status_code=400, detail='"suffix_messages" must be a list of tasks (each task is a list of messages).')
        if len(suffix) < 1 or len(suffix) > 256:
            raise HTTPException(status_code=400, detail='"suffix_messages" must have between 1 and 256 tasks.')

        for task in suffix:
            for m in task:
                if not isinstance(m, dict) or "role" not in m or "content" not in m:
                    raise HTTPException(status_code=400, detail="Each suffix message must have role+content.")

        return len(suffix), suffix

    def _to_openai_choices(self, payloads: List[Any]) -> Any:
        """Convert multiple payloads to OpenAI-style choices."""
        base = payloads[0]

        if hasattr(base, "choices") and hasattr(base, "model_dump"):
            new_choices = []
            for i, p in enumerate(payloads):
                c0 = p.choices[0]
                # Ensure index matches OpenAI n semantics
                try:
                    c0.index = i
                except Exception:
                    c0 = c0.model_copy(update={"index": i})
                new_choices.append(c0)

                # Aggregate usage statistics
                base.usage.completion_tokens += p.usage.completion_tokens
                base.usage.prompt_tokens += p.usage.prompt_tokens
                base.usage.total_tokens += p.usage.total_tokens

            base.choices = new_choices
            return base

        raise HTTPException(status_code=500, detail=f"Unsupported engine response type for fanout. {type(base)}")
    
    async def chat_completions( # if you need to use /v1/completions use def completions(..)
        self,
        model_input: Dict[str, Any],
        request: Request,
    ) -> Any:
        # alias to predict, so that both /predict and (/sync)/v1/chat/completions work
        return await self.predict(model_input, request)
```

### Fan-out generation configuration

To deploy the above example, create a new directory, for example, `fanout` and create a `fanout/model/model.py` file.

Then create the following `config.yaml` at `fanout/config.yaml`

```yaml config.yaml theme={"system"}
model_name: Multi-Generation-LLM
resources:
  accelerator: H100
  cpu: '2'
  memory: 20Gi
  use_gpu: true
trt_llm:
  build:
    base_model: decoder
    checkpoint_repository:
      source: HF
      repo: "meta-llama/Llama-3.1-8B-Instruct"
    quantization_type: fp8
  runtime:
    served_model_name: "Multi-Generation-LLM"
```

Finally, push the model with `truss push`. TRT-LLM engine builds require a published deployment and do not support `--watch` mode.

## How routing works

Custom engine builder exposes two endpoint paths:

* **`/predict`**: calls your `predict()` method. Use this for custom request formats, business logic, or non-OpenAI patterns.
* **`/v1/chat/completions`**: calls `chat_completions()` if defined, otherwise falls back to `predict()`. Use this for OpenAI-compatible clients.

To make both paths work, define `chat_completions` as an alias to `predict` (as shown in the fan-out example above). If you only define `predict`, the `/v1/chat/completions` endpoint still works but goes through your `predict` method with the raw OpenAI-format input.

## Limitations and considerations

### What custom engine builder cannot do

**Custom tokenization:**

* Cannot modify the underlying tokenizer implementation
* Cannot add custom vocabulary or special tokens
* Must use the model's native tokenization

**Model architecture changes:**

* Cannot modify the TensorRT-LLM engine structure
* Cannot change attention mechanisms or model layers
* Cannot add custom model components

### When to use standard engine instead

* Standard chat completions without special requirements
* No need for business logic integration

## Monitoring and debugging

### Request tracing

```python theme={"system"}
import uuid
import os
from contextlib import asynccontextmanager

class Model:
    def __init__(self, trt_llm, **kwargs):
        self._engine = trt_llm["engine"]
        self._trace_enabled = os.environ.get("enable_tracing", True)
        
    @asynccontextmanager
    async def _trace_request(self, request_id: str):
        """Context manager for request tracing."""
        if self._trace_enabled:
            print(f"[TRACE] Start: {request_id}")
            start_time = time.time()
        
        try:
            yield
        finally:
            if self._trace_enabled:
                duration = time.time() - start_time
                print(f"[TRACE] End: {request_id} (duration: {duration:.3f}s)")
                
    async def predict(self, model_input: Dict[str, Any], request: Request) -> Any:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        
        async with self._trace_request(request_id):
            # Main logic here
            response = await self._engine.chat_completions(request=request, model_input=model_input)
            return response
```

## Related

* [Engine-Builder-LLM overview](/engines/engine-builder-llm/overview): Main engine documentation.
* [Engine-Builder-LLM configuration](/engines/engine-builder-llm/engine-builder-config): Complete reference config.
* [Examples section](/examples/overview): Deployment examples.
* [Chains documentation](/development/chain/overview): Multi-model workflows.
