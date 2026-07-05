"""SSE passthrough contract: `stream: true` on /v1/chat/completions must
flow token-by-token through the router — the first event leaves the router
while the backend is still generating (no full-response buffering), and the
event-stream media type + economics headers survive the hop.

The timing assertion runs against RouterState.proxy_chat_stream's generator
(the only router-owned code on the streaming path — the endpoint wraps it in
starlette's StreamingResponse, which streams by contract). Starlette's
TestClient buffers streamed responses through its portal, so it can't
observe inter-chunk timing; it verifies the HTTP-layer contract instead."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from starlette.testclient import TestClient

from router_app.main import RouterState, get_app

TOKEN_DELAY_S = 0.25
N_TOKENS = 3


class StreamingChatHandler(BaseHTTPRequestHandler):
    finished_at = None          # set when the LAST byte has been written

    def do_GET(self):
        body = b'{"status": "ok"}'
        self.send_response(200 if self.path == "/healthz" else 404)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("X-TTFT-Ms", "5.0")
        self.send_header("X-Completion-Tokens", str(N_TOKENS))
        self.end_headers()
        for i in range(N_TOKENS):
            chunk = ("data: " + json.dumps(
                {"choices": [{"delta": {"content": f"tok{i} "}}]}) + "\n\n")
            self.wfile.write(chunk.encode())
            self.wfile.flush()
            time.sleep(TOKEN_DELAY_S)
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()
        type(self).finished_at = time.monotonic()

    def log_message(self, *args):
        pass


def _configs(tmp_path, url):
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        "backends:\n"
        "  llm-sim:\n"
        "    path: services/llm\n"
        "    tier: realtime\n"
        "    target: cpu\n"
        "    engine: max\n")
    policy = tmp_path / "policy.yaml"
    policy.write_text(
        "tiers:\n"
        "  realtime: {max_latency_ms: 250, prefer: lowest_latency,"
        " ttft_ms: 500, tpot_ms: 60}\n"
        "cost_table: {local-docker: 0.1}\n"
        "cache: {enabled: false}\n"
        "affinity: {enabled: false, prefix_tokens: 32, capacity: 8}\n"
        "endpoints:\n"
        "  llm-sim:\n"
        f"    - {{id: sim, provider: local-docker, url: {url}}}\n")
    return registry, policy


@pytest.fixture()
def sse_backend(tmp_path, monkeypatch):
    class Handler(StreamingChatHandler):
        finished_at = None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    monkeypatch.setenv("ROUTER_QUEUE_DIR", str(tmp_path / "queue"))
    yield _configs(tmp_path, url), Handler
    server.shutdown()


BODY = {"model": "llm-sim", "stream": True, "max_tokens": 8,
        "messages": [{"role": "user", "content": "count to three"}]}


def test_stream_generator_is_unbuffered(sse_backend):
    (registry, policy), handler = sse_backend
    state = RouterState(registry, policy)
    gen, choice, hdrs, status = state.proxy_chat_stream(
        "llm-sim", dict(BODY), {})
    assert status == 200
    assert hdrs["content-type"].startswith("text/event-stream")
    first_data_at = None
    lines = []
    for chunk in gen:
        for line in chunk.splitlines():
            if not line.startswith("data:"):
                continue
            if first_data_at is None:
                first_data_at = time.monotonic()
                # THE contract: the first token left the router while the
                # backend was still generating. A buffering proxy cannot
                # pass this — the backend finishes N_TOKENS * TOKEN_DELAY_S
                # later.
                assert handler.finished_at is None, \
                    "router buffered the whole stream before forwarding"
            lines.append(line)
    # the full stream arrived, terminator included, one event per token
    assert lines[-1] == "data: [DONE]"
    contents = [json.loads(l[5:])["choices"][0]["delta"]["content"]
                for l in lines[:-1]]
    assert contents == ["tok0 ", "tok1 ", "tok2 "]
    # and the backend did finish well after the first client-visible token
    assert handler.finished_at - first_data_at > TOKEN_DELAY_S
    # router-measured economics were recorded once the stream closed
    snap = state.ledger.snapshot()
    key = "llm-sim@local-docker"
    assert snap["backends"][key]["requests"] == 1


def test_stream_endpoint_media_type_and_headers(sse_backend):
    (registry, policy), handler = sse_backend
    app = get_app(registry, policy, start_background=False)
    with TestClient(app) as client:
        with client.stream("POST", "/v1/chat/completions?model=llm-sim",
                           json=BODY) as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith(
                "text/event-stream")
            # backend economics + routing metadata forwarded on our response
            assert resp.headers["X-TTFT-Ms"] == "5.0"
            assert resp.headers["X-Completion-Tokens"] == str(N_TOKENS)
            assert resp.headers["X-Replica"] == "sim"
            assert resp.headers["X-Backend"] == "local-docker"
            lines = [l for l in resp.iter_lines() if l.startswith("data:")]
    assert lines[-1] == "data: [DONE]"
    assert len(lines) == N_TOKENS + 1
