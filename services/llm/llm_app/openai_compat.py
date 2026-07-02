"""Live OpenAI-compatible pool adapters — Baseten (Truss) and vLLM (RunPod).

Both pools expose the same OpenAI chat surface, so one adapter implements the
wire protocol and the subclasses carry provider identity + auth. Unlike the
sim (which *models* economics), these MEASURE them: generate() always streams
upstream, timing wall-clock TTFT and decode, and attributes cost from the
pool's $/hr price — so the router's /v1/costs and the devboard show real
numbers, per the mission's SLO-AUDITOR rule.

Stdlib-only (urllib streaming): Bazel targets and tests need no pip deps. The
HTTP call is injectable (`opener`) so unit tests are deterministic and I/O-free.

Keys come from env vars only (BASETEN_API_KEY / VLLM_API_KEY), never config
files. No GPU or network is required anywhere in tests: without a base_url the
factory falls back to the local sim for these engines.
"""

import json
import os
import time
import urllib.request

from llm_app.adapter import BackendAdapter, ChatRequest, Generation
from llm_app.economics import Plan, estimate_tokens


def _urllib_opener(url: str, payload: dict, headers: dict, timeout: float):
    """POST and yield response lines as they arrive (SSE-friendly)."""
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            yield raw.decode("utf-8", "replace").rstrip("\r\n")


class OpenAICompatAdapter(BackendAdapter):
    """Any OpenAI-compatible chat endpoint, with measured economics."""

    engine = "openai-compat"
    target = "gpu"
    auth_env: str | None = None    # env var holding the API key
    auth_scheme = "Bearer"         # Authorization: <scheme> <key>
    auth_required = False
    send_stream_usage = False      # vLLM supports stream_options include_usage
    backend_label = "openai-compat"
    chat_path = "/v1/chat/completions"   # Baseten custom Truss overrides -> /predict
    health_path = "/v1/models"           # None => cheap always-ok liveness

    def __init__(self, name: str, base_url: str, model_id: str | None = None,
                 usd_per_hour: float = 0.0, timeout_s: float = 120.0,
                 clock=time.monotonic, opener=_urllib_opener):
        if not base_url:
            raise ValueError(
                f"{type(self).__name__} requires a base_url (the pool's "
                "OpenAI-compatible endpoint). Without one the factory serves "
                "the local sim instead.")
        key = os.environ.get(self.auth_env) if self.auth_env else None
        if self.auth_required and not key:
            raise ValueError(
                f"{type(self).__name__} requires {self.auth_env} in the "
                "environment (env vars only — never files or arguments).")
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id or name
        self.usd_per_hour = usd_per_hour
        self.timeout_s = timeout_s
        self._clock = clock
        self._opener = opener
        self._key = key

    # ---- wire helpers ------------------------------------------------------

    def _headers(self) -> dict:
        if self._key:
            return {"Authorization": f"{self.auth_scheme} {self._key}"}
        return {}

    def _payload(self, request: ChatRequest, stream: bool) -> dict:
        payload = {
            "model": self.model_id,
            "messages": [{"role": m.role, "content": m.content}
                         for m in request.messages],
            "max_tokens": request.max_tokens,
            "stream": stream,
        }
        if stream and self.send_stream_usage:
            payload["stream_options"] = {"include_usage": True}
        return payload

    def _sse_events(self, request: ChatRequest):
        """Yield parsed JSON chunks from the upstream SSE stream."""
        url = f"{self.base_url}{self.chat_path}"
        for line in self._opener(url, self._payload(request, stream=True),
                                 self._headers(), self.timeout_s):
            if not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                return
            try:
                yield json.loads(data)
            except json.JSONDecodeError:
                continue  # partial/keepalive line — never crash the stream

    # ---- BackendAdapter ----------------------------------------------------

    def capabilities(self) -> set[str]:
        return {"chat"}

    def info(self) -> dict:
        base = super().info()
        base.update({"backend": self.backend_label, "model_id": self.model_id,
                     "base_url": self.base_url,
                     "usd_per_hour": self.usd_per_hour})
        return base

    def models(self) -> list[str]:
        return [self.model_id]

    def generate(self, request: ChatRequest) -> Generation:
        """Stream upstream (even for non-stream clients) to measure real TTFT
        and decode time; return the assembled completion with a measured Plan.
        """
        t0 = self._clock()
        first_token_at = None
        tokens: list[str] = []
        usage: dict = {}
        request_id = f"chatcmpl-{self.backend_label}"
        for chunk in self._sse_events(request):
            request_id = chunk.get("id", request_id)
            if chunk.get("usage"):
                usage = chunk["usage"]
            for choice in chunk.get("choices", []):
                delta = (choice.get("delta") or {}).get("content")
                if delta:
                    if first_token_at is None:
                        first_token_at = self._clock()
                    tokens.append(delta)
        t_end = self._clock()

        text = "".join(tokens)
        ttft_ms = ((first_token_at or t_end) - t0) * 1000.0
        decode_ms = (t_end - first_token_at) * 1000.0 if first_token_at else 0.0
        prompt_tokens = usage.get("prompt_tokens",
                                  estimate_tokens(request.prompt_text()))
        completion_tokens = usage.get("completion_tokens",
                                      estimate_tokens(text) if text else 0)
        # Real cost: this request's wall-clock share of the instance-hour.
        est_cost_usd = self.usd_per_hour * ((t_end - t0) / 3600.0)
        plan = Plan(prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cold_start_ms=0.0,       # cold starts belong to the pool,
                    prefill_ms=ttft_ms,      # measured: TTFT = prefill view
                    decode_ms=decode_ms,     # measured
                    cache_hit=False,
                    est_cost_usd=est_cost_usd)
        return Generation(request_id=request_id, model=self.name,
                          tokens=tokens or [text], plan=plan)

    def stream_raw(self, request: ChatRequest):
        """Pass-through SSE for streaming clients (used by the HTTP layer)."""
        url = f"{self.base_url}{self.chat_path}"
        done = False
        for line in self._opener(url, self._payload(request, stream=True),
                                 self._headers(), self.timeout_s):
            if not line:
                continue
            out = line if line.startswith("data:") else f"data: {line}"
            done = done or out.strip() == "data: [DONE]"
            yield out
        if not done:
            yield "data: [DONE]"

    def healthz(self) -> dict:
        # health_path=None: the pool endpoint has no cheap health route (or
        # pinging it would wake a scaled-to-zero replica and cost money), so
        # report the proxy's own liveness — real backend failures surface on
        # actual requests and the router ejects on those.
        if self.health_path is None:
            return {"status": "ok"}
        try:
            req = urllib.request.Request(
                f"{self.base_url}{self.health_path}", headers=self._headers())
            with urllib.request.urlopen(req, timeout=5) as resp:
                return {"status": "ok" if resp.status == 200 else "down"}
        except Exception:  # noqa: BLE001 — health probe must never raise
            return {"status": "down"}


class BasetenAdapter(OpenAICompatAdapter):
    """Truss-deployed model on Baseten (primary pool).

    A custom Truss model.py is invoked at `/environments/production/predict`
    (Bearer auth), NOT an OpenAI `/v1/chat/completions` — that path is
    Engine-Builder only. base_url is the env-scoped endpoint, e.g.
    https://model-<id>.api.baseten.co/environments/production . The model.py
    speaks OpenAI request/response JSON and streams SSE `data:` lines, so the
    inherited SSE machinery works once chat_path points at /predict.
    """

    engine = "baseten"
    auth_env = "BASETEN_API_KEY"
    auth_scheme = "Bearer"          # Baseten model invocation prefers Bearer
    auth_required = True
    backend_label = "baseten-truss"
    chat_path = "/predict"
    health_path = None              # no cheap health route; don't wake on poll


class VllmAdapter(OpenAICompatAdapter):
    """Self-hosted vLLM OpenAI server (RunPod pool). Auth optional (Bearer)."""

    engine = "vllm"
    auth_env = "VLLM_API_KEY"
    auth_scheme = "Bearer"
    auth_required = False
    send_stream_usage = True
    backend_label = "vllm-openai"
