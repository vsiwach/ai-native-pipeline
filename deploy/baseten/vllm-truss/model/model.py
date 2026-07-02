"""Truss model — OpenAI-compatible chat surface over vLLM (Baseten pool).

Truss idiom: class Model with __init__(**kwargs) / load() / predict(). We run
vLLM's AsyncLLMEngine in-process and expose an OpenAI-shaped chat-completions
payload through predict(), streaming when requested. The router's
BasetenAdapter translates between the contract surface and this model.

Keys/secrets come from Baseten workspace secrets (hf_access_token) — nothing
sensitive lives in the repo.
"""

import os
import time
import uuid


class Model:
    def __init__(self, **kwargs):
        self._secrets = kwargs.get("secrets") or {}
        self._config = kwargs.get("config") or {}
        self._engine = None
        self._model_id = os.environ.get("MODEL_ID", "Qwen/Qwen3-8B")

    def load(self):
        # Import inside load() so `truss push` metadata steps don't need GPU deps.
        from vllm import AsyncEngineArgs
        from vllm.engine.async_llm_engine import AsyncLLMEngine

        hf_token = self._secrets.get("hf_access_token")
        if hf_token:
            os.environ["HF_TOKEN"] = hf_token
        # Optional quantization/dtype for small single-GPU SKUs (T4 + AWQ).
        extra = {}
        if os.environ.get("QUANTIZATION"):
            extra["quantization"] = os.environ["QUANTIZATION"]
        if os.environ.get("DTYPE"):
            extra["dtype"] = os.environ["DTYPE"]
        self._engine = AsyncLLMEngine.from_engine_args(
            AsyncEngineArgs(
                model=self._model_id,
                max_model_len=int(os.environ.get("MAX_MODEL_LEN", "8192")),
                gpu_memory_utilization=0.90,
                **extra,
            )
        )

    async def predict(self, request: dict):
        """OpenAI chat-completions in, OpenAI chat-completions out.

        request: {messages, max_tokens?, temperature?, stream?} — the subset in
        contracts/llm.openapi.yaml. Streaming yields SSE-shaped chunk dicts.
        """
        from vllm import SamplingParams

        messages = request.get("messages", [])
        prompt = self._to_prompt(messages)
        params = SamplingParams(
            max_tokens=int(request.get("max_tokens", 256)),
            temperature=float(request.get("temperature", 0.7)),
        )
        req_id = f"chatcmpl-{uuid.uuid4().hex[:20]}"
        created = int(time.time())
        stream = bool(request.get("stream", False))
        results = self._engine.generate(prompt, params, req_id)

        if stream:
            async def gen():
                # Yield OpenAI-style SSE `data:` lines. Baseten streams these
                # bytes straight through, so the router's BasetenAdapter (which
                # parses `data:` lines) measures real TTFT/TPOT. A trailing
                # usage chunk carries token counts; then [DONE].
                sent = 0
                n_out = 0
                async for out in results:
                    text = out.outputs[0].text
                    n_out = len(out.outputs[0].token_ids)
                    delta, sent = text[sent:], len(text)
                    if delta:
                        yield self._sse(self._chunk(
                            req_id, created, {"content": delta}))
                n_in = len(out.prompt_token_ids) if 'out' in dir() else 0
                yield self._sse(self._chunk(req_id, created, {}, finish="stop"))
                yield self._sse({"id": req_id, "object": "chat.completion.chunk",
                                 "choices": [],
                                 "usage": {"prompt_tokens": n_in,
                                           "completion_tokens": n_out,
                                           "total_tokens": n_in + n_out}})
                yield "data: [DONE]\n\n"
            return gen()

        final = None
        async for out in results:
            final = out
        text = final.outputs[0].text if final else ""
        n_out = len(final.outputs[0].token_ids) if final else 0
        n_in = len(final.prompt_token_ids) if final else 0
        return {
            "id": req_id,
            "object": "chat.completion",
            "created": created,
            "model": self._model_id,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": n_in,
                "completion_tokens": n_out,
                "total_tokens": n_in + n_out,
            },
        }

    def _to_prompt(self, messages):
        # Qwen3 chat template is applied by vLLM's tokenizer when available;
        # fall back to a simple role-tagged join.
        try:
            tok = self._engine.engine.tokenizer.tokenizer
            return tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except Exception:
            return "\n".join(f"{m['role']}: {m['content']}" for m in messages) + "\nassistant:"

    def _chunk(self, req_id, created, delta, finish=None):
        return {
            "id": req_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": self._model_id,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }

    @staticmethod
    def _sse(obj):
        import json as _json
        return f"data: {_json.dumps(obj)}\n\n"
