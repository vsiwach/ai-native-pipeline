"""LLM serving app — OpenAI-compatible surface over a configured BackendAdapter.

Routes (per contracts/llm.openapi.yaml):
  GET  /healthz              liveness
  GET  /v1/info              identity + capabilities + economics
  GET  /v1/models            OpenAI model list
  POST /v1/chat/completions  stream + non-stream      (chat adapters)
  POST /v1/predict           back-compat passthrough  (predict adapters)

The app is adapter-agnostic: `factory.build_adapter()` picks the engine from
env (which the registry/manifest supplies). Swapping engine/target changes no
code here and no code in the router.
"""

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from llm_app.adapter import ChatRequest
from llm_app.factory import build_adapter
from llm_app.serialize import (completion_body, economics_headers,
                               models_body, sse_stream)


def get_app(adapter=None) -> FastAPI:
    backend = adapter or build_adapter()
    app = FastAPI(title=f"llm-{backend.name}", version="1.0")
    app.state.backend = backend
    caps = backend.capabilities()

    # Fault injection for chaos drills (tools/chaos.py). Env-gated: absent
    # CHAOS_ENABLED=1, no chaos routes exist and the hot path is untouched.
    chaos = {"latency_ms": 0.0, "error_rate": 0.0}
    app.state.chaos = chaos
    if os.environ.get("CHAOS_ENABLED") == "1":
        @app.get("/chaos")
        def chaos_get():
            return chaos

        @app.post("/chaos")
        async def chaos_set(request: Request):
            body = await request.json()
            chaos["latency_ms"] = float(body.get("latency_ms", 0.0))
            chaos["error_rate"] = float(body.get("error_rate", 0.0))
            return chaos

    def _chaos_gate():
        """Returns an error response, or None to proceed."""
        if chaos["latency_ms"] > 0:
            import time as _t
            _t.sleep(chaos["latency_ms"] / 1000.0)
        if chaos["error_rate"] > 0:
            import random as _r
            if _r.random() < chaos["error_rate"]:
                return JSONResponse(
                    {"error": {"type": "chaos_injected_5xx"}},
                    status_code=500)
        return None

    @app.get("/healthz")
    def healthz():
        return backend.healthz()

    @app.get("/v1/info")
    def info():
        # contract fields (model/version/tier/target) + LLM capability advert
        data = {"model": backend.name, "version": "1.0",
                "tier": os.environ.get("TIER", "realtime"),
                "target": backend.target}
        data.update(backend.info())
        return data

    @app.get("/v1/models")
    def models():
        return models_body(backend.models())

    if "chat" in caps:
        @app.post("/v1/chat/completions")
        async def chat_completions(request: Request):
            body = await request.json()
            injected = _chaos_gate()
            if injected is not None:
                return injected
            req = ChatRequest.from_dict(body)
            if req.stream and hasattr(backend, "stream_raw"):
                # Live backends stream through untouched — real tokens at
                # real times. Re-pacing a buffered generation (below) is
                # only correct for the sim, which models its own timing.
                return StreamingResponse(
                    (f"{line}\n\n" for line in backend.stream_raw(req)),
                    media_type="text/event-stream",
                    headers={"X-Backend": backend.name})
            gen = backend.generate(req)
            headers = economics_headers(gen, backend.name)
            if req.stream:
                return StreamingResponse(
                    sse_stream(gen), media_type="text/event-stream",
                    headers=headers)
            return JSONResponse(completion_body(gen), headers=headers)

    if "predict" in caps:
        @app.post("/v1/predict")
        async def predict(request: Request):
            body = await request.json()
            return JSONResponse(backend.predict(body))

    return app


app = get_app() if os.environ.get("LLM_AUTOSTART", "1") == "1" else None
