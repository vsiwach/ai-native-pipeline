"""docs-assist — a retrieval-grounded Modular knowledge agent, OpenAI-compatible.

The demo's migrated route. Exposes /v1/chat/completions (streaming + non-
streaming). Each request: retrieve top-k chunks from the KB -> inject as
system context -> forward to the configured upstream model server (MAX or
vLLM or a frontier API — all OpenAI-compatible) -> stream back with
citation metadata headers.

Env:
  UPSTREAM_BASE_URL   e.g. http://<runpod-a100>:8000/v1   (MAX / vLLM)
  UPSTREAM_MODEL      e.g. Qwen/Qwen2.5-14B-Instruct
  UPSTREAM_API_KEY    optional bearer for frontier pass-through
  KB_INDEX            path to modular_kb.sqlite
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from retrieval import Retriever, build_context

UPSTREAM = os.environ.get("UPSTREAM_BASE_URL", "http://localhost:8000/v1").rstrip("/")
MODEL = os.environ.get("UPSTREAM_MODEL", "Qwen/Qwen2.5-14B-Instruct")
API_KEY = os.environ.get("UPSTREAM_API_KEY", "")
KB = os.environ.get("KB_INDEX", str(Path(__file__).parent / "kb" / "modular_kb.sqlite"))

SYSTEM = (
    "You are docs-assist, an unofficial demo assistant for the Modular platform "
    "(MAX, Mojo, Mammoth), grounded ONLY in the context below, which comes from "
    "Modular's public documentation. Answer concisely. Cite sources inline as "
    "[1], [2] matching the numbered context blocks. If the context does not "
    "contain the answer, say so — never invent Modular facts.\n\nCONTEXT:\n{context}"
)

app = FastAPI(title="docs-assist", version="0.1.0")
_retriever: Retriever | None = None


def retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever(KB)
    return _retriever


@app.get("/healthz")
async def healthz():
    ok = Path(KB).exists()
    return {"status": "ok" if ok else "degraded", "kb": ok, "upstream": UPSTREAM}


@app.get("/v1/info")
async def info():
    return {
        "name": "docs-assist",
        "kind": "agent",
        "model": MODEL,
        "upstream": UPSTREAM,
        "kb_index": KB,
        "disclosure": "unofficial demo built on public Modular docs",
    }


@app.post("/v1/chat/completions")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    question = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
    )
    t0 = time.perf_counter()
    chunks = retriever().search(question, k=4)
    retrieval_ms = round((time.perf_counter() - t0) * 1000, 1)
    grounded = [{"role": "system", "content": SYSTEM.format(context=build_context(chunks))}]
    grounded += [m for m in messages if m.get("role") != "system"]

    upstream_body = dict(body, model=body.get("model", MODEL), messages=grounded)
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    cite_meta = json.dumps(
        [{"n": i + 1, "url": c.url, "title": c.title} for i, c in enumerate(chunks)]
    )

    client = httpx.AsyncClient(timeout=120)
    if body.get("stream"):
        async def gen():
            async with client.stream(
                "POST", f"{UPSTREAM}/chat/completions", json=upstream_body, headers=headers
            ) as r:
                async for line in r.aiter_lines():
                    if line:
                        yield line + "\n\n"
            await client.aclose()

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={"X-Citations": cite_meta, "X-Retrieval-Ms": str(retrieval_ms)},
        )

    r = await client.post(f"{UPSTREAM}/chat/completions", json=upstream_body, headers=headers)
    await client.aclose()
    resp = JSONResponse(r.json(), status_code=r.status_code)
    resp.headers["X-Citations"] = cite_meta
    resp.headers["X-Retrieval-Ms"] = str(retrieval_ms)
    return resp
