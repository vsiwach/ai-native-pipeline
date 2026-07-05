"""model_apis manifest tests — one catalog-driven manifest expands to one
registry backend per hosted Model API. Testable surface: the expansion is
faithful to the catalog (names, slugs, uniqueness), every entry carries the
contract fields the router depends on, and the committed Dockerfile is
exactly the manifest's render (drift guard)."""

import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent


def load_manifest():
    spec = importlib.util.spec_from_file_location(
        "_manifest_model_apis", HERE / "service.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ModelApisManifestTest(unittest.TestCase):
    def setUp(self):
        self.services = load_manifest().SERVICES
        self.catalog = json.loads(
            (REPO / "deploy" / "baseten" / "model-apis.json").read_text())

    def test_one_backend_per_catalog_model(self):
        self.assertEqual(len(self.services), len(self.catalog["models"]))
        self.assertGreater(len(self.services), 0)
        aliases = [s.name for s in self.services]
        self.assertEqual(len(aliases), len(set(aliases)), "aliases collide")
        self.assertEqual(sorted(aliases),
                         sorted(m["alias"] for m in self.catalog["models"]))

    def test_slugs_map_to_model_id(self):
        by_alias = {m["alias"]: m["slug"] for m in self.catalog["models"]}
        for svc in self.services:
            self.assertEqual(svc.model_id, by_alias[svc.name])

    def test_contract_fields(self):
        for svc in self.services:
            self.assertEqual(svc.path, "services/model_apis")
            self.assertEqual(svc.engine, "baseten-api")
            self.assertEqual(svc.target, "gpu")
            self.assertEqual(svc.tier, "standard")
            self.assertFalse(svc.scale_to_zero)  # shared serverless: always-on

    def test_dockerfile_is_exact_manifest_render(self):
        self.assertEqual(self.services[0].image.to_dockerfile(),
                         (HERE / "Dockerfile").read_text())


if __name__ == "__main__":
    unittest.main()
