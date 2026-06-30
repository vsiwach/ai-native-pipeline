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
            req = ChatRequest.from_dict(body)
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
