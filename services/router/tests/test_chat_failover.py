"""Chat-path failover: a dead replica is marked unhealthy and the next one
serves the request — for BOTH chat modes. One sick pool must never become a
client-facing 502 while a healthy pool exists (the /v1/predict guarantee,
extended to chat)."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from router_app.main import RouterState


class ChatHandler(BaseHTTPRequestHandler):
    mode = "ok"          # class attr: "ok" | "fail" (500s every chat call)

    def do_GET(self):
        if self.path == "/healthz":
            self._send(200, {"status": "ok"})
        else:
            self._send(404, {})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        if self.path != "/v1/chat/completions":
            self._send(404, {})
            return
        if type(self).mode == "fail":
            self._send(500, {"error": {"type": "backend_boom"}})
            return
        body = json.dumps({
            "id": "chatcmpl-mock", "object": "chat.completion",
            "model": "qwen3-8b",
            "choices": [{"index": 0, "message": {
                "role": "assistant", "content": "ok"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-TTFT-Ms", "42.0")
        self.send_header("X-Completion-Tokens", "2")
        self.end_headers()
        self.wfile.write(body)

    def _send(self, status, obj):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture()
def chat_state(tmp_path, monkeypatch):
    """RouterState with one DEAD replica (closed port) and one live mock —
    the dead one deliberately first in the policy."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), ChatHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    alive = f"http://127.0.0.1:{server.server_address[1]}"
    dead = "http://127.0.0.1:1"     # nothing listens on port 1

    registry = tmp_path / "registry.yaml"
    registry.write_text(
        "backends:\n"
        "  qwen3-8b:\n"
        "    path: services/qwen3_8b\n"
        "    tier: realtime\n"
        "    target: gpu\n"
        "    engine: vllm\n")
    policy = tmp_path / "policy.yaml"
    policy.write_text(
        "tiers:\n"
        "  realtime: {max_latency_ms: 250, prefer: lowest_latency,"
        " ttft_ms: 500, tpot_ms: 60}\n"
        "cost_table: {pool-a: 1.0, pool-b: 1.0}\n"
        "cache: {enabled: false}\n"
        "affinity: {enabled: false, prefix_tokens: 32, capacity: 8}\n"
        "endpoints:\n"
        "  qwen3-8b:\n"
        f"    - {{id: pool-a, provider: pool-a, url: {dead}}}\n"
        f"    - {{id: pool-b, provider: pool-b, url: {alive}}}\n")
    monkeypatch.setenv("ROUTER_QUEUE_DIR", str(tmp_path / "queue"))
    state = RouterState(Path(registry), Path(policy))
    yield state, dead, alive
    server.shutdown()


BODY = {"model": "qwen3-8b", "max_tokens": 8,
        "messages": [{"role": "user", "content": "hi"}]}


def test_nonstream_chat_fails_over_to_healthy_replica(chat_state):
    state, dead, alive = chat_state
    resp, choice = state.proxy_chat("qwen3-8b", dict(BODY), {})
    assert resp.status_code == 200
    assert choice.url == alive
    # the dead replica was marked unhealthy for future selections
    assert state.poller.status_for(dead).healthy is False
    kinds = [e["kind"] for e in state.events.recent(20)]
    assert "failover" in kinds


def test_stream_chat_fails_over_before_committing(chat_state):
    state, dead, alive = chat_state
    gen, choice, hdrs, status = state.proxy_chat_stream(
        "qwen3-8b", {**BODY, "stream": True}, {})
    assert choice.url == alive
    assert status == 200
    list(gen)  # drain so bookkeeping closes cleanly
    assert state.poller.status_for(dead).healthy is False


def test_all_replicas_dead_raises_no_healthy_backend(chat_state):
    from router_app.policy import NoHealthyBackend
    state, dead, alive = chat_state
    state.poller.mark_unhealthy(alive)
    state.poller.mark_unhealthy(dead)
    with pytest.raises(NoHealthyBackend):
        state.proxy_chat("qwen3-8b", dict(BODY), {})


@pytest.fixture()
def sick_and_healthy(tmp_path, monkeypatch):
    """Two LIVE mocks: replica one answers 500 on chat, replica two 200."""
    class Sick(ChatHandler):
        mode = "fail"

    class Healthy(ChatHandler):
        mode = "ok"

    servers = []
    urls = []
    for handler in (Sick, Healthy):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers.append(srv)
        urls.append(f"http://127.0.0.1:{srv.server_address[1]}")
    sick, healthy = urls

    registry = tmp_path / "registry.yaml"
    registry.write_text(
        "backends:\n"
        "  qwen3-8b:\n"
        "    path: services/qwen3_8b\n"
        "    tier: realtime\n"
        "    target: gpu\n"
        "    engine: vllm\n")
    policy = tmp_path / "policy.yaml"
    policy.write_text(
        "tiers:\n"
        "  realtime: {max_latency_ms: 250, prefer: lowest_latency,"
        " ttft_ms: 500, tpot_ms: 60}\n"
        "cost_table: {pool-a: 1.0, pool-b: 1.0}\n"
        "cache: {enabled: false}\n"
        "affinity: {enabled: false, prefix_tokens: 32, capacity: 8}\n"
        "endpoints:\n"
        "  qwen3-8b:\n"
        f"    - {{id: pool-a, provider: pool-a, url: {sick}}}\n"
        f"    - {{id: pool-b, provider: pool-b, url: {healthy}}}\n")
    monkeypatch.setenv("ROUTER_QUEUE_DIR", str(tmp_path / "queue"))
    state = RouterState(Path(registry), Path(policy))
    yield state, sick, healthy, Sick, Healthy
    for srv in servers:
        srv.shutdown()


def test_backend_5xx_fails_over_and_records_breach(sick_and_healthy):
    state, sick, healthy, _, _ = sick_and_healthy
    resp, choice = state.proxy_chat("qwen3-8b", dict(BODY), {})
    # the healthy replica answered the client...
    assert resp.status_code == 200
    assert choice.url == healthy
    # ...and the sick replica's 5xx was recorded as an SLO breach
    breaches = [e for e in state.events.recent(20) if e["kind"] == "slo_breach"]
    assert any(b["replica"] == "pool-a" for b in breaches)


def test_all_replicas_5xx_returns_real_status_not_200(sick_and_healthy):
    state, sick, healthy, Sick, Healthy = sick_and_healthy
    # sicken BOTH replicas: the client must see the 5xx, never a 200
    Healthy.mode = "fail"
    try:
        resp, choice = state.proxy_chat("qwen3-8b", dict(BODY), {})
        assert resp.status_code == 500
    finally:
        Healthy.mode = "ok"
