"""/v1/dev/loadgen — the console's "generate load" button: start a bounded
synthetic run, watch counters move, refuse a second concurrent run, stop
early. The run posts to `target` (a mock OpenAI server here; the router
itself in production, so shadow/metrics see ordinary traffic)."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from starlette.testclient import TestClient

from router_app.main import get_app
from tests.conftest import write_configs


class ChatBackend(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        body = json.dumps({"choices": [{"message": {
            "role": "assistant", "content": "ok"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):
        pass


@pytest.fixture()
def load_client(tmp_path, monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), ChatBackend)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    target = f"http://127.0.0.1:{server.server_address[1]}"
    monkeypatch.setenv("ROUTER_QUEUE_DIR", str(tmp_path / "queue"))
    registry, policy = write_configs(
        tmp_path,
        "  house-price-reg:\n"
        "    - provider: local-docker\n"
        f"      url: {target}\n")
    app = get_app(registry, policy, start_background=False)
    with TestClient(app) as client:
        client.target = target
        client.state = app.state.router_state
        yield client
    server.shutdown()


def _wait_finished(client, timeout_s=15):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        s = client.get("/v1/dev/loadgen").json()
        if s.get("finished"):
            return s
        time.sleep(0.1)
    raise AssertionError(f"load run never finished: {s}")


def test_idle_status(load_client):
    s = load_client.get("/v1/dev/loadgen").json()
    assert s == {"running": False, "sent": 0}


def test_bounded_run_counts_and_finishes(load_client):
    c = load_client
    s = c.post("/v1/dev/loadgen", json={
        "action": "start", "target": c.target, "route": "any",
        "rps": 20, "duration_s": 1.0, "stream_ratio": 0.0}).json()
    assert s["running"] is True
    s = _wait_finished(c)
    assert s["running"] is False
    assert s["sent"] > 0
    assert s["ok"] == s["sent"]
    assert s["errors"] == 0
    # the run left a start + done trail in the events log
    kinds = [(e["kind"], e.get("action"))
             for e in c.state.events.recent(20)]
    assert ("loadgen", "start") in kinds
    assert ("loadgen", "done") in kinds


def test_second_start_while_running_is_409_then_stop(load_client):
    c = load_client
    r = c.post("/v1/dev/loadgen", json={
        "action": "start", "target": c.target, "route": "any",
        "rps": 2, "duration_s": 30, "stream_ratio": 0.0})
    assert r.status_code == 200
    r = c.post("/v1/dev/loadgen", json={"action": "start",
                                        "target": c.target})
    assert r.status_code == 409
    s = c.post("/v1/dev/loadgen", json={"action": "stop"}).json()
    deadline = time.monotonic() + 5
    while s["running"] and time.monotonic() < deadline:
        time.sleep(0.05)
        s = c.get("/v1/dev/loadgen").json()
    assert s["running"] is False


def test_caps_are_enforced(load_client):
    c = load_client
    s = c.post("/v1/dev/loadgen", json={
        "action": "start", "target": c.target, "route": "any",
        "rps": 999, "duration_s": 99999, "stream_ratio": 0.0}).json()
    assert s["rps"] <= 20.0
    assert s["duration_s"] <= 600.0
    c.post("/v1/dev/loadgen", json={"action": "stop"})
