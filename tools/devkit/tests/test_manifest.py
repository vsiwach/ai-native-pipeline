"""Tests for the resources-as-code layer: manifest.Image/service + sync."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import manifest  # noqa: E402
import registry  # noqa: E402
import sync  # noqa: E402


class ImageTest(unittest.TestCase):
    def test_chaining_renders_dockerfile_in_order(self):
        img = (
            manifest.Image.debian_slim("3.11")
            .workdir("/srv")
            .pip_install("fastapi==0.115.12")
            .expose(8080)
            .cmd(["python", "app.py"])
        )
        df = img.to_dockerfile()
        self.assertTrue(df.startswith("FROM python:3.11-slim\n"))
        self.assertIn("WORKDIR /srv", df)
        self.assertIn("RUN pip install --no-cache-dir fastapi==0.115.12", df)
        self.assertIn("EXPOSE 8080", df)
        self.assertIn('CMD ["python", "app.py"]', df)

    def test_image_is_immutable_per_step(self):
        base = manifest.Image.debian_slim()
        derived = base.pip_install("numpy")
        self.assertNotEqual(base.to_dockerfile(), derived.to_dockerfile())

    def test_dockerfile_requires_base(self):
        with self.assertRaises(ValueError):
            manifest.Image().to_dockerfile()


class ServiceTest(unittest.TestCase):
    def test_registry_entry_matches_registry_add_format(self):
        svc = manifest.service(
            name="foo", path="services/foo", tier="standard", target="cpu",
            max_replicas=3, scale_to_zero=True,
        )
        self.assertEqual(
            svc.to_registry_entry(),
            "  foo:\n"
            "    path: services/foo\n"
            "    tier: standard\n"
            "    target: cpu\n"
            "    max_replicas: 3\n"
            "    scale_to_zero: true\n",
        )

    def test_rejects_bad_tier_and_target(self):
        with self.assertRaises(ValueError):
            manifest.service("a", "services/a", "turbo", "cpu")
        with self.assertRaises(ValueError):
            manifest.service("a", "services/a", "batch", "tpu")


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        svc_dir = self.root / "services" / "foo"
        svc_dir.mkdir(parents=True)
        (svc_dir / "service.py").write_text(
            "import sys\n"
            f"sys.path.insert(0, {str(Path(__file__).resolve().parent.parent)!r})\n"
            "from manifest import service\n"
            "SERVICE = service('foo', 'services/foo', 'realtime', 'gpu',\n"
            "                   max_replicas=2, scale_to_zero=False)\n"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_sync_generates_registry_loadable_by_router(self):
        self.assertEqual(sync.sync(self.root), 0)
        backends = registry.load(self.root)
        self.assertEqual(len(backends), 1)
        self.assertEqual(backends[0], {
            "name": "foo", "path": "services/foo", "tier": "realtime",
            "target": "gpu", "max_replicas": "2", "scale_to_zero": "false",
        })

    def test_check_passes_after_sync_and_fails_on_drift(self):
        sync.sync(self.root)
        self.assertEqual(sync.sync(self.root, check=True), 0)
        # Mutate the file on disk -> drift -> check must fail.
        registry.registry_path(self.root).write_text("backends:\n")
        self.assertEqual(sync.sync(self.root, check=True), 1)


if __name__ == "__main__":
    unittest.main()
