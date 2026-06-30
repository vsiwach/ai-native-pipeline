"""MaxContainer — proxies a REAL `max serve` (Modular MAX, OpenAI-compatible).

Enabled only when the manifest says `target: gpu` and MAX_BASE_URL points at a
running endpoint. Never instantiated in tests and never required for them — the
sim is the default. See the service README for the exact `max serve` command.
"""

import json

from llm_app.adapter import BackendAdapter, ChatRequest, Generation
from llm_app.economics import Plan, estimate_tokens


class MaxContainer(BackendAdapter):
    engine = "max"
    target = "gpu"

    def __init__(self, name: str, base_url: str, model_id: str | None = None):
        if not base_url:
            raise ValueError(
                "MaxContainer requires MAX_BASE_URL (the max serve endpoint). "
                "Use engine=max + target=cpu (MaxLocalSim) when no GPU.")
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id or name

    def capabilities(self) -> set[str]:
        return {"chat"}

    def info(self) -> dict:
        base = super().info()
        base.update({"backend": "max-container", "model_id": self.model_id,
                     "base_url": self.base_url})
        return base

    def generate(self, request: ChatRequest) -> Generation:
        # httpx is in requirements.txt; imported lazily so the module loads
        # (and tests import it) without the dep present.
        import httpx

        payload = {
            "model": self.model_id,
            "messages": [{"role": m.role, "content": m.content}
                         for m in request.messages],
            "max_tokens": request.max_tokens,
            "stream": False,
        }
        resp = httpx.post(f"{self.base_url}/v1/chat/completions",
                          json=payload, timeout=120)
        resp.raise_for_status()
        body = resp.json()
        text = body["choices"][0]["message"]["content"]
        usage = body.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens",
                                  estimate_tokens(request.prompt_text()))
        completion_tokens = usage.get("completion_tokens", estimate_tokens(text))
        # real engine reports usage, not our sim economics; cost left to the
        # router's cost table for the gpu provider.
        plan = Plan(prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens, cold_start_ms=0.0,
                    prefill_ms=0.0, decode_ms=0.0, cache_hit=False,
                    est_cost_usd=0.0)
        return Generation(request_id=body.get("id", "chatcmpl-max"),
                          model=self.name, tokens=[text], plan=plan)

    def stream_raw(self, request: ChatRequest):
        """Pass-through SSE from the real endpoint (used by the HTTP layer
        when stream=True)."""
        import httpx

        payload = {
            "model": self.model_id,
            "messages": [{"role": m.role, "content": m.content}
                         for m in request.messages],
            "max_tokens": request.max_tokens, "stream": True,
        }
        with httpx.stream("POST", f"{self.base_url}/v1/chat/completions",
                          json=payload, timeout=120) as resp:
            for line in resp.iter_lines():
                if line:
                    yield line if line.startswith("data:") else f"data: {line}"
        yield "data: [DONE]"

    def healthz(self) -> dict:
        try:
            import httpx
            r = httpx.get(f"{self.base_url}/v1/models", timeout=5)
            return {"status": "ok" if r.status_code == 200 else "down"}
        except Exception:  # noqa: BLE001 — health probe must never raise
            return {"status": "down"}
