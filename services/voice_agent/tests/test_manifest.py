"""voice-agent manifest tests — declaration-only service (the app is
services/docs_assist): pin the contract fields the router depends on and
that the committed Dockerfile is exactly the manifest's render."""

import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def load_manifest():
    spec = importlib.util.spec_from_file_location(
        "_manifest_voice_agent", HERE / "service.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VoiceAgentManifestTest(unittest.TestCase):
    def setUp(self):
        self.svc = load_manifest().SERVICE

    def test_contract_fields(self):
        self.assertEqual(self.svc.name, "voice-agent")
        self.assertEqual(self.svc.path, "services/voice_agent")
        self.assertEqual(self.svc.tier, "realtime")   # voice SLO tier
        self.assertEqual(self.svc.target, "cpu")
        self.assertEqual(self.svc.engine, "openai-proxy")

    def test_image_is_the_docs_assist_app(self):
        df = self.svc.image.to_dockerfile()
        self.assertIn("services/docs_assist/app.py", df)
        self.assertIn("services/docs_assist/kb", df)

    def test_dockerfile_is_exact_manifest_render(self):
        self.assertEqual(self.svc.image.to_dockerfile(),
                         (HERE / "Dockerfile").read_text())


if __name__ == "__main__":
    unittest.main()
