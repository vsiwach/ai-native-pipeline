"""Shared fixtures: temp registry/policy files and a stdlib mock backend
(per Phase 3: mock backends with http.server, no FastAPI in the fakes)."""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class MockBackendHandler(BaseHTTPRequestHandler):
    healthy = True
    prediction = {"median_house_value": 123, "currency": "USD"}

    def _send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/healthz" and type(self).healthy:
            self._send(200, {"status": "ok"})
        else:
            self._send(503, {"status": "down"})

    def do_POST(self):
        if not type(self).healthy:
            self._send(503, {"error": "down"})
            return
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        if self.path == "/v1/predict":
            self._send(200, type(self).prediction)
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, *args):
        pass


@pytest.fixture()
def mock_backend():
    """Yields (base_url, handler_class). Toggle handler_class.healthy to
    simulate a dead backend."""
    class Handler(MockBackendHandler):
        healthy = True

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}", Handler
    server.shutdown()


def write_configs(tmp_path: Path, endpoints_yaml: str) -> tuple[Path, Path]:
    registry = tmp_path / "inference-registry.yaml"
    registry.write_text(
        "backends:\n"
        "  house-price-reg:\n"
        "    path: services/inference\n"
        "    tier: standard\n"
        "    target: cpu\n"
    )
    policy = tmp_path / "routing-policy.yaml"
    policy.write_text(
        "tiers:\n"
        "  realtime: {max_latency_ms: 250, prefer: lowest_latency}\n"
        "  standard: {max_latency_ms: 2000, prefer: lowest_cost}\n"
        "  batch: {max_latency_ms: null, prefer: lowest_cost, queue: true}\n"
        "cost_table:\n"
        "  gcp-cloudrun-cpu: 0.40\n"
        "  aws-apprunner-cpu: 0.46\n"
        "  local-docker: 0.10\n"
        "cache: {enabled: true, ttl_s: 300, backend: in_memory}\n"
        "endpoints:\n" + endpoints_yaml
    )
    return registry, policy


@pytest.fixture()
def router_client(tmp_path, mock_backend, monkeypatch):
    """TestClient wired to one healthy mock backend; background threads off
    (tests drive the poller/worker directly)."""
    from starlette.testclient import TestClient

    from router_app.main import get_app

    url, handler = mock_backend
    monkeypatch.setenv("ROUTER_QUEUE_DIR", str(tmp_path / "queue"))
    registry, policy = write_configs(
        tmp_path,
        f"  house-price-reg:\n    - provider: local-docker\n      url: {url}\n",
    )
    app = get_app(registry, policy, start_background=False)
    with TestClient(app) as client:
        client.handler = handler
        client.state = app.state.router_state
        yield client
