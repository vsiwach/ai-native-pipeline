"""qwen3-8b manifest tests — the service is declaration-only (the app is
services/llm's llm_app), so what's testable IS the declaration: the
SERVICE contract fields the router/registry depend on, and that the
committed Dockerfile is exactly the manifest's render (drift guard)."""

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def load_manifest():
    spec = importlib.util.spec_from_file_location(
        "_manifest_qwen3_8b", HERE / "service.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Qwen38bManifestTest(unittest.TestCase):
    def setUp(self):
        self.svc = load_manifest().SERVICE

    def test_contract_fields(self):
        self.assertEqual(self.svc.name, "qwen3-8b")
        self.assertEqual(self.svc.path, "services/qwen3_8b")
        self.assertEqual(self.svc.tier, "realtime")   # voice SLO tier
        self.assertEqual(self.svc.target, "gpu")
        self.assertEqual(self.svc.engine, "vllm")
        self.assertEqual(self.svc.model_id, "Qwen/Qwen3-8B")

    def test_registry_entry_carries_llm_fields(self):
        entry = self.svc.to_registry_entry()
        for needle in ("engine: vllm", "model_id: Qwen/Qwen3-8B",
                       "cold_start_s: 25.0", "kv_ttl_s: 300.0"):
            self.assertIn(needle, entry)

    def test_dockerfile_is_exact_manifest_render(self):
        self.assertEqual(self.svc.image.to_dockerfile(),
                         (HERE / "Dockerfile").read_text())


if __name__ == "__main__":
    unittest.main()
