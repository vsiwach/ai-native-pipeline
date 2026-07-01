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

    def test_rejects_bad_section(self):
        with self.assertRaises(ValueError):
            manifest.service("a", "services/a", "batch", "cpu",
                             section="middleware")

    def test_rejects_bad_engine(self):
        with self.assertRaises(ValueError):
            manifest.service("a", "services/a", "realtime", "cpu",
                             engine="tensorrt")

    def test_llm_fields_omitted_when_unset_keeps_entry_byte_stable(self):
        # a non-LLM service must render exactly as before (no new lines)
        svc = manifest.service("foo", "services/foo", "standard", "cpu")
        self.assertNotIn("engine:", svc.to_registry_entry())
        self.assertNotIn("cold_start_s:", svc.to_registry_entry())

    def test_llm_fields_render_in_order_when_set(self):
        svc = manifest.service(
            "llm-sim", "services/llm", "realtime", "cpu", engine="max",
            model_id="google/gemma-3-12b-it", cold_start_s=8.0, kv_ttl_s=300.0,
        )
        self.assertEqual(
            svc.to_registry_entry(),
            "  llm-sim:\n"
            "    path: services/llm\n"
            "    tier: realtime\n"
            "    target: cpu\n"
            "    max_replicas: 3\n"
            "    scale_to_zero: true\n"
            "    engine: max\n"
            "    model_id: google/gemma-3-12b-it\n"
            "    cold_start_s: 8.0\n"
            "    kv_ttl_s: 300.0\n",
        )

    def test_section_defaults_to_backends(self):
        svc = manifest.service("a", "services/a", "batch", "cpu")
        self.assertEqual(svc.section, "backends")


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

    def test_check_fails_after_manifest_edit_without_resync(self):
        sync.sync(self.root)
        manifest_py = self.root / "services" / "foo" / "service.py"
        manifest_py.write_text(
            manifest_py.read_text().replace("'realtime'", "'batch'"))
        self.assertEqual(sync.sync(self.root, check=True), 1)
        sync.sync(self.root)  # regenerate -> clean again
        self.assertEqual(sync.sync(self.root, check=True), 0)
        self.assertEqual(registry.load(self.root)[0]["tier"], "batch")

    def test_services_section_round_trip(self):
        infra_dir = self.root / "services" / "gateway"
        infra_dir.mkdir(parents=True)
        (infra_dir / "service.py").write_text(
            "import sys\n"
            f"sys.path.insert(0, {str(Path(__file__).resolve().parent.parent)!r})\n"
            "from manifest import service\n"
            "SERVICE = service('gateway', 'services/gateway', 'realtime',\n"
            "                   'cpu', scale_to_zero=False, section='services')\n"
        )
        self.assertEqual(sync.sync(self.root), 0)
        infra = registry.load(self.root, section="services")
        self.assertEqual(len(infra), 1)
        self.assertEqual(infra[0]["name"], "gateway")
        self.assertEqual(infra[0]["scale_to_zero"], "false")
        # backends section still only holds routing targets
        backends = registry.load(self.root)
        self.assertEqual([b["name"] for b in backends], ["foo"])
        # deterministic render: a second sync is a no-op
        before = registry.registry_path(self.root).read_text()
        sync.sync(self.root)
        self.assertEqual(registry.registry_path(self.root).read_text(), before)


if __name__ == "__main__":
    unittest.main()
