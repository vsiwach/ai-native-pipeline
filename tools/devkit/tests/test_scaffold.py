"""Tests for the service scaffolder — including that a generated service's
own tests pass and its server honors the inference contract."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import registry  # noqa: E402
import scaffold  # noqa: E402


class ScaffoldTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_creates_all_required_artifacts(self):
        scaffold.create_service(self.root, "demo", "standard", "cpu")
        svc = self.root / "services" / "demo"
        for rel in ("service.py", "app.py", "Dockerfile", "BUILD.bazel",
                    "README.md", "requirements.txt", "tests/test_app.py"):
            self.assertTrue((svc / rel).exists(), f"missing {rel}")
        self.assertTrue(
            (self.root / ".github" / "workflows" / "service-demo.yml").exists()
        )

    def test_manifest_is_typed_and_drives_the_registry(self):
        import sync
        scaffold.create_service(self.root, "demo", "batch", "gpu")
        manifest_src = (self.root / "services/demo/service.py").read_text()
        self.assertIn("from manifest import Image, service", manifest_src)
        self.assertNotIn("SERVICE = {", manifest_src)  # typed, not a dict
        # registry was generated via sync and stays drift-free
        self.assertEqual(sync.sync(self.root, check=True), 0)
        entry = registry.load(self.root)[0]
        self.assertEqual((entry["tier"], entry["target"]), ("batch", "gpu"))

    def test_dockerfile_matches_manifest_image_chain(self):
        import runpy
        scaffold.create_service(self.root, "demo", "standard", "cpu")
        rendered = runpy.run_path(
            str(self.root / "services/demo/service.py"))["image"].to_dockerfile()
        self.assertEqual(
            (self.root / "services/demo/Dockerfile").read_text(), rendered)

    def test_registers_backend(self):
        scaffold.create_service(self.root, "demo", "realtime", "gpu")
        backends = registry.load(self.root)
        self.assertEqual(backends[0]["name"], "demo")
        self.assertEqual(backends[0]["tier"], "realtime")
        self.assertEqual(backends[0]["target"], "gpu")

    def test_rejects_bad_names_and_duplicates(self):
        for bad in ("Demo", "x", "has_underscore", "9starts-with-digit"):
            with self.assertRaises(ValueError, msg=bad):
                scaffold.create_service(self.root, bad, "standard", "cpu")
        scaffold.create_service(self.root, "demo", "standard", "cpu")
        with self.assertRaises(ValueError):
            scaffold.create_service(self.root, "demo", "standard", "cpu")

    def test_generated_service_tests_pass(self):
        scaffold.create_service(self.root, "demo", "standard", "cpu")
        result = subprocess.run(
            [sys.executable, str(self.root / "services/demo/tests/test_app.py")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_generated_info_endpoint_declares_tier(self):
        scaffold.create_service(self.root, "demo", "batch", "cpu")
        app_src = (self.root / "services/demo/app.py").read_text()
        self.assertIn('COST_TIER = "batch"', app_src)
        # the contract fields must all be served by /v1/info
        for field in ("model", "version", "cost_tier"):
            self.assertIn(field, app_src)

    def test_generated_service_passes_dev_check_artifact_rules(self):
        import checks
        scaffold.create_service(self.root, "demo", "standard", "cpu")
        self.assertEqual(checks.check_service_artifacts(self.root), 0)
        self.assertEqual(registry.validate(self.root), [])


if __name__ == "__main__":
    unittest.main()
