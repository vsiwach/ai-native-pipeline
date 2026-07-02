"""Live OpenAI-compatible pool adapters — Baseten (Truss + Model APIs) and
vLLM (RunPod).

All pools expose the same OpenAI chat surface, so one adapter implements the
wire protocol and the subclasses carry provider identity + auth. Unlike the
sim (which *models* economics), these MEASURE them: generate() always streams
upstream, timing wall-clock TTFT and decode, and attributes cost either from
the pool's $/hr price (dedicated instances) or from per-token prices (hosted
Model APIs) — so the router's /v1/costs and the devboard show real numbers,
per the mission's SLO-AUDITOR rule.

Reliability: upstream failures are CLASSIFIED (UpstreamError) instead of
leaking urllib tracebacks, and transient ones (connect failures, 429, 5xx)
are retried with jittered exponential backoff — but never after the stream
has started, so tokens are never double-billed or duplicated.

Stdlib-only (urllib streaming): Bazel targets and tests need no pip deps. The
HTTP call is injectable (`opener`) so unit tests are deterministic and I/O-free.

Keys come from env vars only (BASETEN_API_KEY / VLLM_API_KEY), never config
files. No GPU or network is required anywhere in tests: without a base_url the
factory falls back to the local sim for these engines.
"""

import json
import os
import random
import time
import urllib.error
import urllib.request

from llm_app.adapter import BackendAdapter, ChatRequest, Generation
from llm_app.economics import Plan, estimate_tokens


class UpstreamError(Exception):
    """A classified upstream failure. `status` is the upstream HTTP status
    (0 for transport-level failures), `kind` one of rate_limited |
    upstream_5xx | bad_request | unreachable. `retryable` drives the
    adapter's backoff and the router's failover decision."""

    def __init__(self, status: int, kind: str, message: str, retryable: bool):
        super().__init__(message)
        self.status = status
        self.kind = kind
        self.retryable = retryable


def classify_error(exc: Exception) -> UpstreamError:
    """Map a raw transport exception onto the UpstreamError taxonomy."""
    if isinstance(exc, urllib.error.HTTPError):
        try:
            detail = exc.read().decode("utf-8", "replace")[:300]
        except Exception:  # noqa: BLE001 — a closed body must not mask the code
            detail = ""
        msg = f"upstream HTTP {exc.code}: {detail or exc.reason}"
        if exc.code == 429:
            return UpstreamError(429, "rate_limited", msg, retryable=True)
        if exc.code >= 500:
            return UpstreamError(exc.code, "upstream_5xx", msg, retryable=True)
        return UpstreamError(exc.code, "bad_request", msg, retryable=False)
    return UpstreamError(0, "unreachable", f"upstream unreachable: {exc}",
                         retryable=True)


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
                 usd_per_1m_prompt: float | None = None,
                 usd_per_1m_completion: float | None = None,
                 retries: int = 2, backoff_s: float = 0.5,
                 clock=time.monotonic, opener=_urllib_opener,
                 sleeper=time.sleep):
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
        # Hosted APIs bill per token, dedicated instances per hour. When
        # per-token prices are set they win; otherwise cost is the request's
        # wall-clock share of the instance-hour.
        self.usd_per_1m_prompt = usd_per_1m_prompt
        self.usd_per_1m_completion = usd_per_1m_completion
        self.timeout_s = timeout_s
        self.retries = retries
        self.backoff_s = backoff_s
        self._clock = clock
        self._opener = opener
        self._sleep = sleeper
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

    def _stream_lines(self, request: ChatRequest):
        """Open the upstream stream and yield raw lines, retrying transient
        failures with jittered exponential backoff — but ONLY while nothing
        has been yielded yet. Once the stream has started, a failure raises
        (retrying would duplicate tokens and double-bill). Raises
        UpstreamError, never raw urllib errors."""
        url = f"{self.base_url}{self.chat_path}"
        attempt = 0
        while True:
            yielded = False
            try:
                for line in self._opener(url,
                                         self._payload(request, stream=True),
                                         self._headers(), self.timeout_s):
                    yielded = True
                    yield line
                return
            except UpstreamError:
                raise                     # already classified (nested opener)
            except Exception as exc:  # noqa: BLE001 — classify every transport
                err = classify_error(exc)
                if yielded or not err.retryable or attempt >= self.retries:
                    raise err from exc
                attempt += 1
                delay = self.backoff_s * (2 ** (attempt - 1))
                self._sleep(delay + random.uniform(0, delay * 0.25))

    def _sse_events(self, request: ChatRequest):
        """Yield parsed JSON chunks from the upstream SSE stream."""
        for line in self._stream_lines(request):
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
                delta = choice.get("delta") or {}
                content = delta.get("content")
                # reasoning models stream thinking deltas before (sometimes
                # instead of) content — they ARE the first token for TTFT,
                # they just don't join the visible text
                if content or delta.get("reasoning") \
                        or delta.get("reasoning_content"):
                    if first_token_at is None:
                        first_token_at = self._clock()
                if content:
                    tokens.append(content)
        t_end = self._clock()

        text = "".join(tokens)
        ttft_ms = ((first_token_at or t_end) - t0) * 1000.0
        decode_ms = (t_end - first_token_at) * 1000.0 if first_token_at else 0.0
        prompt_tokens = usage.get("prompt_tokens",
                                  estimate_tokens(request.prompt_text()))
        completion_tokens = usage.get("completion_tokens",
                                      estimate_tokens(text) if text else 0)
        if self.usd_per_1m_prompt is not None \
                or self.usd_per_1m_completion is not None:
            # Real cost, per-token billing (hosted Model APIs).
            est_cost_usd = (
                prompt_tokens / 1e6 * (self.usd_per_1m_prompt or 0.0)
                + completion_tokens / 1e6 * (self.usd_per_1m_completion or 0.0))
        else:
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
        """Pass-through SSE for streaming clients (used by the HTTP layer).

        Failure semantics: before anything is yielded, UpstreamError
        propagates (the HTTP layer turns it into a real error status the
        router's failover can act on). After the stream has started, the
        error becomes a structured SSE frame + [DONE] — the transport is
        already committed to 200, so silence is the only worse option."""
        done = False
        started = False
        lines = self._stream_lines(request)
        while True:
            try:
                line = next(lines)
            except StopIteration:
                break
            except UpstreamError as err:
                if not started:
                    raise
                yield ("data: " + json.dumps(
                    {"error": {"type": err.kind, "message": str(err),
                               "upstream_status": err.status}}))
                break
            started = True
            if not line:
                continue
            out = line if line.startswith("data:") else f"data: {line}"
            done = done or out.strip() == "data: [DONE]"
            yield out
        if not done:
            yield "data: [DONE]"

    # upstream health is cached and refreshed OFF the request path: the
    # router polls /healthz every couple of seconds, and a live upstream
    # round-trip inside each poll both flaps (upstream jitter > poll timeout
    # reads as "down") and hammers the vendor for nothing
    health_cache_ttl_s = 30.0

    def healthz(self) -> dict:
        # health_path=None: the pool endpoint has no cheap health route (or
        # pinging it would wake a scaled-to-zero replica and cost money), so
        # report the proxy's own liveness — real backend failures surface on
        # actual requests and the router ejects on those.
        if self.health_path is None:
            return {"status": "ok"}
        cache = getattr(self, "_health_cache", None)
        if cache is None:
            cache = self._health_cache = {"status": "ok", "at": None,
                                          "refreshing": False}
        now = time.monotonic()
        if not cache["refreshing"] and (
                cache["at"] is None
                or now - cache["at"] > self.health_cache_ttl_s):
            cache["refreshing"] = True
            import threading
            threading.Thread(target=self._refresh_health,
                             daemon=True).start()
        return {"status": cache["status"], "upstream_checked_at": cache["at"]}

    def _refresh_health(self) -> None:
        try:
            req = urllib.request.Request(
                f"{self.base_url}{self.health_path}", headers=self._headers())
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = "ok" if resp.status == 200 else "down"
        except Exception:  # noqa: BLE001 — health probe must never raise
            status = "down"
        self._health_cache.update(status=status, at=time.monotonic(),
                                  refreshing=False)


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
    # Engine-Builder deploys are OpenAI-compatible: base_url is the sync
    # endpoint (…/environments/production/sync) and chat is /v1/chat/completions,
    # so the standard OpenAI SSE machinery applies. health_path stays None so a
    # health poll reports proxy liveness instead of waking a scaled-to-zero
    # replica (which would bill).
    chat_path = "/v1/chat/completions"
    health_path = None


class VllmAdapter(OpenAICompatAdapter):
    """Self-hosted vLLM OpenAI server (RunPod pool). Auth optional (Bearer)."""

    engine = "vllm"
    auth_env = "VLLM_API_KEY"
    auth_scheme = "Bearer"
    auth_required = False
    send_stream_usage = True
    backend_label = "vllm-openai"


class BasetenModelAPIAdapter(OpenAICompatAdapter):
    """Baseten hosted Model APIs (https://inference.baseten.co) — the
    serverless multi-tenant catalog (Kimi, GLM, DeepSeek, Nemotron, ...).

    Unlike the Truss path there is NOTHING to provision: any model in the
    catalog is one config entry away (deploy/baseten/model-apis.json, itself
    generated from the live /v1/models listing by `manage.py catalog`).
    Billing is per token, so per-token prices drive cost attribution.
    health_path stays None: chaos drills proved the upstream /v1/models
    listing is intermittently slow (>5s), and mapping listing jitter to
    "pool down" flapped pools that were serving chat fine. Health here means
    proxy liveness; real upstream failures surface on the request path
    (classified 5xx -> SLO breach -> incident agent)."""

    engine = "baseten-api"
    auth_env = "BASETEN_API_KEY"
    auth_scheme = "Bearer"
    auth_required = True
    send_stream_usage = True
    backend_label = "baseten-model-api"
    chat_path = "/v1/chat/completions"
    health_path = None
