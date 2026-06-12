"""Tests for the registry reader/writer/validator."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import registry  # noqa: E402


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_missing_file_is_empty(self):
        self.assertEqual(registry.load(self.root), [])

    def test_add_then_load_roundtrip(self):
        (self.root / "services" / "foo").mkdir(parents=True)
        registry.add(self.root, "foo", "realtime", "gpu", "services/foo")
        backends = registry.load(self.root)
        self.assertEqual(len(backends), 1)
        self.assertEqual(backends[0], {
            "name": "foo", "tier": "realtime",
            "target": "gpu", "path": "services/foo",
            "max_replicas": "3", "scale_to_zero": "true",
        })

    def test_add_rejects_duplicate_name(self):
        registry.add(self.root, "foo", "standard", "cpu", "services/foo")
        with self.assertRaises(ValueError):
            registry.add(self.root, "foo", "batch", "cpu", "services/foo")

    def test_add_rejects_bad_tier_and_target(self):
        with self.assertRaises(ValueError):
            registry.add(self.root, "a", "turbo", "cpu", "services/a")
        with self.assertRaises(ValueError):
            registry.add(self.root, "a", "batch", "tpu", "services/a")

    def test_validate_flags_missing_path_and_bad_values(self):
        registry.registry_path(self.root).write_text(
            "backends:\n"
            "  ghost:\n"
            "    tier: warp\n"
            "    target: cpu\n"
            "    path: services/ghost\n"
        )
        problems = registry.validate(self.root)
        self.assertTrue(any("invalid tier" in p for p in problems))
        self.assertTrue(any("does not exist" in p for p in problems))

    def test_validate_clean_registry(self):
        (self.root / "services" / "ok").mkdir(parents=True)
        registry.add(self.root, "ok", "standard", "cpu", "services/ok")
        self.assertEqual(registry.validate(self.root), [])


if __name__ == "__main__":
    unittest.main()
