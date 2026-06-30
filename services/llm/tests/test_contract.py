"""Contract tests for the OpenAI-compatible surface (gates CI):
/healthz, /v1/info, /v1/models, /v1/chat/completions (stream + non-stream)."""

import json


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_info_advertises_capabilities(client):
    body = client.get("/v1/info").json()
    assert body["model"] == "llm-sim"
    assert body["target"] in ("cpu", "gpu")
    assert body["engine"] == "max"
    assert "chat" in body["capabilities"]


def test_models_openai_shape(client):
    body = client.get("/v1/models").json()
    assert body["object"] == "list"
    assert body["data"][0]["id"] == "llm-sim"
    assert body["data"][0]["object"] == "model"


def test_chat_completion_non_stream(client):
    r = client.post("/v1/chat/completions", json={
        "model": "llm-sim",
        "messages": [{"role": "user", "content": "hello there"}],
        "max_tokens": 12, "seed": 3,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert body["choices"][0]["finish_reason"] == "stop"
    assert body["usage"]["completion_tokens"] == 12
    # economics surfaced as headers for the router/devboard
    assert r.headers["x-cache"] in ("hit", "miss")
    assert float(r.headers["x-ttft-ms"]) >= 0
    assert float(r.headers["x-est-cost"]) >= 0


def test_chat_completion_streaming(client):
    r = client.post("/v1/chat/completions", json={
        "model": "llm-sim",
        "messages": [{"role": "user", "content": "stream this please"}],
        "max_tokens": 8, "seed": 5, "stream": True,
    })
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    lines = [ln for ln in r.text.splitlines() if ln.startswith("data:")]
    assert lines[-1] == "data: [DONE]"
    # reassemble the streamed deltas into the full completion
    content = ""
    for ln in lines[:-1]:
        chunk = json.loads(ln[len("data: "):])
        assert chunk["object"] == "chat.completion.chunk"
        content += chunk["choices"][0]["delta"].get("content", "")
    assert len(content) > 0


def test_stream_and_nonstream_agree_on_text(client):
    payload = {"model": "llm-sim",
               "messages": [{"role": "user", "content": "same prompt seed"}],
               "max_tokens": 10, "seed": 42}
    non_stream = client.post("/v1/chat/completions", json=payload).json()
    full = non_stream["choices"][0]["message"]["content"]

    streamed = client.post("/v1/chat/completions",
                           json={**payload, "stream": True}).text
    content = ""
    for ln in streamed.splitlines():
        if ln.startswith("data:") and ln != "data: [DONE]":
            content += json.loads(ln[6:])["choices"][0]["delta"].get("content", "")
    assert content == full
