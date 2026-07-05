"""Certified-migration route controls: shadow mirroring behind the policy's
`routes:` flag, GET shadow-stats, POST promote (swap primary for candidate,
via the release engine) and POST rollback (restore previous) — plus the
/v1/costs `routes` + `pools` extensions the demo console polls."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from router_app.main import get_app


class ChatHandler(BaseHTTPRequestHandler):
    content = "primary answer"

    def do_GET(self):
        self._send(200 if self.path == "/healthz" else 404, {"status": "ok"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        if self.path != "/v1/chat/completions":
            self._send(404, {})
            return
        body = json.dumps({
            "id": "chatcmpl-mock", "object": "chat.completion",
            "model": "docs-assist",
            "choices": [{"index": 0, "message": {
                "role": "assistant", "content": type(self).content}}],
            "usage": {"completion_tokens": 3},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-TTFT-Ms", "40.0")
        self.send_header("X-Citations", '[{"n": 1, "url": "https://d/x"}]')
        self.send_header("X-Completion-Tokens", "3")
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
def migration_client(tmp_path, monkeypatch):
    """Router app with a docs-assist route: primary + shadow candidate are
    two live mock chat servers with distinguishable answers."""
    class Primary(ChatHandler):
        content = "primary answer [1]"

    class Candidate(ChatHandler):
        content = "candidate answer [1]"

    servers, urls = [], []
    for handler in (Primary, Candidate):
        srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers.append(srv)
        urls.append(f"http://127.0.0.1:{srv.server_address[1]}")
    primary_url, candidate_url = urls

    registry = tmp_path / "registry.yaml"
    registry.write_text(
        "backends:\n"
        "  docs-assist:\n"
        "    path: services/docs_assist\n"
        "    tier: realtime\n"
        "    target: cpu\n"
        "    engine: openai-proxy\n")
    policy = tmp_path / "policy.yaml"
    policy.write_text(
        "tiers:\n"
        "  realtime: {max_latency_ms: 250, prefer: lowest_latency,"
        " ttft_ms: 500, tpot_ms: 60}\n"
        "cost_table: {frontier-api: 10.0, shadow-candidate: 0.5}\n"
        "cache: {enabled: false}\n"
        "affinity: {enabled: false, prefix_tokens: 32, capacity: 8}\n"
        "routes:\n"
        "  docs-assist:\n"
        f"    shadow_candidate: {candidate_url}/v1\n"
        "    shadow_id: docs-assist-candidate\n"
        "    shadow_provider: shadow-candidate\n"
        "endpoints:\n"
        "  docs-assist:\n"
        f"    - {{id: frontier, provider: frontier-api, url: {primary_url}}}\n")
    monkeypatch.setenv("ROUTER_QUEUE_DIR", str(tmp_path / "queue"))
    monkeypatch.setenv("SHADOW_LOG_DIR", str(tmp_path / "shadow-logs"))
    monkeypatch.setenv("BENCH_REPORTS_DIR", str(tmp_path / "bench-reports"))
    app = get_app(registry, policy, start_background=False)
    with TestClient(app) as client:
        client.state = app.state.router_state
        client.candidate_url = candidate_url
        yield client
    for srv in servers:
        srv.shutdown()


BODY = {"max_tokens": 8, "messages": [{"role": "user", "content": "q?"}]}


def _chat(client):
    return client.post("/v1/chat/completions?model=docs-assist", json=BODY)


def test_shadow_mirrors_while_primary_serves(migration_client):
    c = migration_client
    resp = _chat(c)
    assert resp.status_code == 200
    # the CLIENT got the primary's answer...
    assert resp.json()["choices"][0]["message"]["content"] == \
        "primary answer [1]"
    assert resp.headers["X-Replica"] == "frontier"
    # ...while the candidate got a mirror of the request
    mirror = c.state.shadows["docs-assist"]
    assert mirror.flush(timeout_s=5)
    rec = json.loads(Path(mirror.log_path).read_text().splitlines()[0])
    assert rec["primary"]["content"] == "primary answer [1]"
    assert rec["candidate"]["content"] == "candidate answer [1]"
    assert rec["candidate"]["citations"]


def test_shadow_stats_endpoint(migration_client):
    c = migration_client
    _chat(c)
    c.state.shadows["docs-assist"].flush(timeout_s=5)
    stats = c.get("/v1/routes/docs-assist/shadow-stats").json()
    assert stats["route"] == "docs-assist"
    assert stats["submitted"] == 1
    assert stats["completed"] == 1
    assert stats["serving"] == "frontier"
    assert stats["release"] is None       # nothing promoted yet


def test_shadow_stats_404_without_candidate(migration_client):
    r = migration_client.get("/v1/routes/nope/shadow-stats")
    assert r.status_code == 404


def test_promote_swaps_primary_then_rollback_restores(migration_client):
    c = migration_client
    r = c.post("/v1/routes/docs-assist/promote")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "promoted"
    assert body["serving"] == "docs-assist-candidate"
    assert body["previous"] == "frontier"
    # traffic now lands on the candidate
    resp = _chat(c)
    assert resp.headers["X-Replica"] == "docs-assist-candidate"
    assert resp.json()["choices"][0]["message"]["content"] == \
        "candidate answer [1]"
    # the release engine recorded the shift and both actions hit the events log
    stats = c.get("/v1/routes/docs-assist/shadow-stats").json()
    assert stats["release"]["state"] == "complete"
    assert [h["action"] for h in stats["release"]["history"]] == \
        ["start", "complete"]
    # promote is idempotent-ish: second call is a no-op status
    assert c.post("/v1/routes/docs-assist/promote").json()["status"] == \
        "already_promoted"
    # rollback restores the frontier primary
    r = c.post("/v1/routes/docs-assist/rollback")
    assert r.json()["status"] == "rolled_back"
    assert _chat(c).headers["X-Replica"] == "frontier"
    kinds = [(e["kind"], e.get("action")) for e in
             c.state.events.recent(50) if e["kind"] == "release"]
    assert ("release", "promote") in kinds
    assert ("release", "rollback") in kinds


def test_rollback_without_promote_is_409(migration_client):
    r = migration_client.post("/v1/routes/docs-assist/rollback")
    assert r.status_code == 409


def test_promote_unknown_route_404(migration_client):
    r = migration_client.post("/v1/routes/nope/promote")
    assert r.status_code == 404


