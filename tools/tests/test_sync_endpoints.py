"""Tests for tools/sync_endpoints.py — terraform outputs -> routing policy."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sync_endpoints  # noqa: E402

POLICY = """\
tiers:
  standard: {max_latency_ms: 2000, prefer: lowest_cost}
cost_table:
  gcp-cloudrun-cpu: 0.40
  aws-apprunner-cpu: 0.46
  local-docker: 0.10
cache: {enabled: true, ttl_s: 300, backend: in_memory}

endpoints:
  house-price-reg:
    - provider: local-docker
      url: http://inference:8080
"""

TF_OUTPUTS = {
    "gcp_urls": {"value": {"inference": "https://inference-gcp.run.app",
                           "router": "https://router-gcp.run.app"}},
    "aws_urls": {"value": {"inference": "https://inference.awsapprunner.com",
                           "router": "https://router.awsapprunner.com"}},
}


class SyncEndpointsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "inference-registry.yaml").write_text(
            "backends:\n"
            "  house-price-reg:\n"
            "    path: services/inference\n"
            "    tier: standard\n"
            "    target: cpu\n"
        )
        self.policy = self.root / "routing-policy.yaml"
        self.policy.write_text(POLICY)

    def tearDown(self):
        self.tmp.cleanup()

    def _merged(self, outputs=TF_OUTPUTS):
        return sync_endpoints.merge(self.policy, outputs, self.root)

    def test_parse_existing_endpoints(self):
        eps = sync_endpoints.parse_endpoints(POLICY)
        self.assertEqual(eps["house-price-reg"][0]["provider"], "local-docker")
        self.assertEqual(eps["house-price-reg"][0]["url"], "http://inference:8080")

    def test_adds_cloud_endpoints_for_backends(self):
        eps = sync_endpoints.parse_endpoints(self._merged())
        providers = {e["provider"]: e["url"] for e in eps["house-price-reg"]}
        self.assertEqual(providers["gcp-cloudrun-cpu"],
                         "https://inference-gcp.run.app")
        self.assertEqual(providers["aws-apprunner-cpu"],
                         "https://inference.awsapprunner.com")

    def test_preserves_local_docker_entry(self):
        eps = sync_endpoints.parse_endpoints(self._merged())
        providers = [e["provider"] for e in eps["house-price-reg"]]
        self.assertIn("local-docker", providers)

    def test_router_is_never_a_routing_target(self):
        merged = self._merged()
        self.assertNotIn("router-gcp.run.app", merged)
        self.assertNotIn("router.awsapprunner.com", merged)

    def test_upsert_is_idempotent(self):
        self.policy.write_text(self._merged())
        twice = self._merged()
        eps = sync_endpoints.parse_endpoints(twice)
        providers = [e["provider"] for e in eps["house-price-reg"]]
        self.assertEqual(len(providers), len(set(providers)))

    def test_non_endpoint_sections_untouched(self):
        merged = self._merged()
        self.assertIn("cost_table:", merged)
        self.assertIn("gcp-cloudrun-cpu: 0.40", merged)
        self.assertIn("cache: {enabled: true", merged)


if __name__ == "__main__":
    unittest.main()
