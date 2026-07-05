"""ROUTER_CORS_ORIGINS: off by default (no CORS headers leak), on for the
demo console's cross-origin polling, with response headers exposed to JS."""

import pytest
from starlette.testclient import TestClient

from router_app.main import get_app
from tests.conftest import write_configs


@pytest.fixture()
def make_client(tmp_path, monkeypatch):
    def _make(cors: str | None):
        if cors is None:
            monkeypatch.delenv("ROUTER_CORS_ORIGINS", raising=False)
        else:
            monkeypatch.setenv("ROUTER_CORS_ORIGINS", cors)
        monkeypatch.setenv("ROUTER_QUEUE_DIR", str(tmp_path / "queue"))
        registry, policy = write_configs(
            tmp_path,
            "  house-price-reg:\n"
            "    - provider: local-docker\n"
            "      url: http://127.0.0.1:1\n")
        return TestClient(get_app(registry, policy, start_background=False))
    return _make


def test_cors_off_by_default(make_client):
    r = make_client(None).get("/v1/costs",
                              headers={"Origin": "http://localhost:8420"})
    assert "access-control-allow-origin" not in r.headers


def test_cors_enabled_for_configured_origin(make_client):
    client = make_client("http://localhost:8420")
    r = client.get("/v1/costs", headers={"Origin": "http://localhost:8420"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:8420"
    # response headers must be readable by the console's JS
    assert r.headers["access-control-expose-headers"] == "*"
    # and preflight for the chat POST succeeds
    r = client.options("/v1/chat/completions", headers={
        "Origin": "http://localhost:8420",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    assert r.status_code == 200
