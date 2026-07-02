"""Env-gated chaos hook in the pool proxy — off by default, injectable when on."""

import os
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from llm_app.main import get_app
from llm_app.sim import MaxLocalSim


def make_client():
    return TestClient(get_app(MaxLocalSim("qwen3-8b")))


BODY = {"model": "qwen3-8b", "max_tokens": 4,
        "messages": [{"role": "user", "content": "hi"}]}


class ChaosHookTest(unittest.TestCase):
    def test_routes_absent_without_env(self):
        client = make_client()
        self.assertEqual(client.get("/chaos").status_code, 404)
        self.assertEqual(client.post("/v1/chat/completions",
                                     json=BODY).status_code, 200)

    def test_injected_5xx_and_clear(self):
        with mock.patch.dict(os.environ, {"CHAOS_ENABLED": "1"}):
            client = make_client()
        r = client.post("/chaos", json={"error_rate": 1.0})
        self.assertEqual(r.json()["error_rate"], 1.0)
        r = client.post("/v1/chat/completions", json=BODY)
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json()["error"]["type"], "chaos_injected_5xx")
        client.post("/chaos", json={})
        self.assertEqual(client.post("/v1/chat/completions",
                                     json=BODY).status_code, 200)

    def test_status_reports_current_injection(self):
        with mock.patch.dict(os.environ, {"CHAOS_ENABLED": "1"}):
            client = make_client()
        client.post("/chaos", json={"latency_ms": 250.0})
        self.assertEqual(client.get("/chaos").json(),
                         {"latency_ms": 250.0, "error_rate": 0.0})


if __name__ == "__main__":
    unittest.main()
