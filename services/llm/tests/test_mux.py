"""ModelAPIMux — catalog-driven multi-model pool: dispatch, catalog loading,
factory wiring, and the keyless sim fallback. No network, no keys."""

import json
import os
import unittest
from unittest import mock

from llm_app.adapter import ChatRequest
from llm_app.factory import build_adapter
from llm_app.mux import ModelAPIMux, build_model_api_mux
from llm_app.openai_compat import BasetenModelAPIAdapter

CATALOG = {
    "source": "GET https://inference.baseten.co/v1/models",
    "fetched_at": "2026-07-02T00:00:00Z",
    "base_url": "https://inference.baseten.co",
    "models": [
        {"alias": "kimi-k2.7-code", "slug": "moonshotai/Kimi-K2.7-Code",
         "usd_per_1m_prompt": 0.95, "usd_per_1m_completion": 4.0},
        {"alias": "glm-5.2", "slug": "zai-org/GLM-5.2",
         "usd_per_1m_prompt": 1.4, "usd_per_1m_completion": 4.4},
        {"alias": "openai-gpt-120b", "slug": "openai/gpt-oss-120b",
         "usd_per_1m_prompt": 0.1, "usd_per_1m_completion": 0.5},
    ],
}


def write_catalog(tmpdir) -> str:
    path = os.path.join(tmpdir, "model-apis.json")
    with open(path, "w") as f:
        json.dump(CATALOG, f)
    return path


def request(model):
    return ChatRequest.from_dict({
        "model": model, "max_tokens": 4,
        "messages": [{"role": "user", "content": "hi"}]})


class MuxDispatchTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()
        self.catalog_path = write_catalog(self.tmp)

    def _sim_mux(self):
        return build_model_api_mux("model-apis",
                                   catalog_path=self.catalog_path)

    def test_serves_every_catalog_model(self):
        mux = self._sim_mux()
        self.assertEqual(mux.models(),
                         ["glm-5.2", "kimi-k2.7-code", "openai-gpt-120b"])
        self.assertEqual(mux.capabilities(), {"chat"})

    def test_dispatches_by_alias_and_slug(self):
        mux = self._sim_mux()
        self.assertEqual(mux.resolve("glm-5.2").name, "glm-5.2")
        self.assertEqual(mux.resolve("zai-org/GLM-5.2").name, "glm-5.2")

    def test_unknown_model_falls_back_to_default(self):
        mux = self._sim_mux()
        # default = cheapest completion price, so probes always resolve
        self.assertEqual(mux.resolve("nonsense").name, "openai-gpt-120b")
        self.assertEqual(mux.default_alias, "openai-gpt-120b")

    def test_generate_routes_to_the_requested_model(self):
        mux = self._sim_mux()
        gen = mux.generate(request("glm-5.2"))
        self.assertEqual(gen.model, "glm-5.2")

    def test_keyless_sims_carry_real_per_token_prices(self):
        mux = self._sim_mux()
        sim = mux.resolve("glm-5.2")
        self.assertEqual(sim.econ.usd_per_1m_completion_tokens, 4.4)
        self.assertEqual(sim.engine, "baseten-api")  # honest pool identity

    def test_info_reports_catalog_provenance(self):
        info = self._sim_mux().info()
        self.assertEqual(info["catalog_source"],
                         "GET https://inference.baseten.co/v1/models")
        self.assertEqual(len(info["served_models"]), 3)

    def test_live_mux_builds_model_api_adapters(self):
        with mock.patch.dict(os.environ, {"BASETEN_API_KEY": "sk-test"}):
            mux = build_model_api_mux(
                "model-apis", base_url="https://inference.baseten.co",
                catalog_path=self.catalog_path)
        sub = mux.resolve("kimi-k2.7-code")
        self.assertIsInstance(sub, BasetenModelAPIAdapter)
        self.assertEqual(sub.model_id, "moonshotai/Kimi-K2.7-Code")
        self.assertEqual(sub.usd_per_1m_completion, 4.0)

    def test_live_mux_requires_key(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BASETEN_API_KEY", None)
            with self.assertRaises(ValueError):
                build_model_api_mux(
                    "model-apis", base_url="https://inference.baseten.co",
                    catalog_path=self.catalog_path)

    def test_default_alias_override(self):
        mux = build_model_api_mux("model-apis",
                                  catalog_path=self.catalog_path,
                                  default_alias="glm-5.2")
        self.assertEqual(mux.resolve("nope").name, "glm-5.2")


class FactoryMuxTest(unittest.TestCase):
    def test_engine_baseten_api_builds_sim_mux_without_base_url(self):
        import tempfile
        catalog = write_catalog(tempfile.mkdtemp())
        env = {"ENGINE": "baseten-api", "MODEL_NAME": "model-apis",
               "MODEL_API_CATALOG": catalog}
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("BASETEN_API_BASE_URL", None)
            adapter = build_adapter()
        self.assertIsInstance(adapter, ModelAPIMux)
        self.assertEqual(adapter.engine, "baseten-api")
        # sim fallback: sub-adapters are sims, not live adapters
        self.assertNotIsInstance(adapter.resolve("glm-5.2"),
                                 BasetenModelAPIAdapter)


class MuxHttpSurfaceTest(unittest.TestCase):
    """The pool's HTTP layer needs zero changes for multi-model serving."""

    def _client(self):
        import tempfile
        from starlette.testclient import TestClient
        from llm_app.main import get_app
        mux = build_model_api_mux(
            "model-apis", catalog_path=write_catalog(tempfile.mkdtemp()))
        return TestClient(get_app(mux))

    def test_v1_models_lists_the_catalog(self):
        ids = {m["id"] for m in self._client().get("/v1/models").json()["data"]}
        self.assertEqual(ids, {"glm-5.2", "kimi-k2.7-code", "openai-gpt-120b"})

    def test_chat_serves_any_catalog_model(self):
        client = self._client()
        for model in ("kimi-k2.7-code", "glm-5.2"):
            r = client.post("/v1/chat/completions", json={
                "model": model, "max_tokens": 4,
                "messages": [{"role": "user", "content": "hello"}]})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["model"], model)


if __name__ == "__main__":
    unittest.main()
