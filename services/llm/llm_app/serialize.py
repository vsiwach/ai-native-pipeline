"""OpenAI-compatible response shaping + SSE pacing — the seam between the pure
economics/adapter layer and HTTP. Pacing uses an injected `sleep` so tests run
instantly while the live server emits real per-token timing.
"""

import json
import time
from typing import Callable, Iterator

from llm_app.adapter import Generation

OBJECT_COMPLETION = "chat.completion"
OBJECT_CHUNK = "chat.completion.chunk"


def economics_headers(gen: Generation, backend: str) -> dict:
    """Headers the router + devboard read to track LLM economics."""
    p = gen.plan
    return {
        "X-Cache": "hit" if p.cache_hit else "miss",
        "X-Backend": backend,
        "X-TTFT-Ms": f"{p.ttft_ms:.2f}",
        "X-Decode-Ms": f"{p.decode_ms:.2f}",
        "X-Tokens-Per-Sec": f"{p.tokens_per_sec:.2f}",
        "X-Est-Cost": f"{p.est_cost_usd:.10f}",
        "X-Prompt-Tokens": str(p.prompt_tokens),
        "X-Completion-Tokens": str(p.completion_tokens),
    }


def completion_body(gen: Generation) -> dict:
    return {
        "id": gen.request_id,
        "object": OBJECT_COMPLETION,
        "model": gen.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": gen.text},
            "finish_reason": "stop",
        }],
        "usage": gen.usage(),
    }


def _chunk(gen: Generation, delta: dict, finish=None) -> str:
    body = {
        "id": gen.request_id, "object": OBJECT_CHUNK, "model": gen.model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
    }
    return f"data: {json.dumps(body)}\n\n"


def sse_stream(gen: Generation, sleep: Callable[[float], None] = time.sleep,
               pace: bool = True) -> Iterator[str]:
    """Yield OpenAI-style SSE chunks, pacing by the plan's simulated timing:
    wait TTFT before the first token, then decode-time between tokens.
    `pace=False` (tests) skips all waits."""
    p = gen.plan
    if pace:
        sleep(p.ttft_ms / 1000)
    yield _chunk(gen, {"role": "assistant"})
    per_token_s = (p.decode_ms / 1000 / len(gen.tokens)) if gen.tokens else 0
    for tok in gen.tokens:
        if pace and per_token_s:
            sleep(per_token_s)
        yield _chunk(gen, {"content": tok})
    yield _chunk(gen, {}, finish="stop")
    yield "data: [DONE]\n\n"


def models_body(model_ids: list[str]) -> dict:
    return {"object": "list",
            "data": [{"id": m, "object": "model", "owned_by": "ai-native-pipeline"}
                     for m in model_ids]}
