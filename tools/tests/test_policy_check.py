"""Tests for tools/policy_check.py against the real governance policy."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import policy_check  # noqa: E402


class PolicyCheckTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = policy_check.load_policy()

    def _check(self, **kw):
        kw.setdefault("requested_by", "claude")
        kw.setdefault("ref", None)
        kw.setdefault("env", None)
        return policy_check.check(policy=self.policy, **kw)

    def test_identities(self):
        self.assertTrue(policy_check.is_agent("claude", self.policy))
        self.assertTrue(policy_check.is_agent("claude[bot]", self.policy))
        self.assertFalse(policy_check.is_agent("vikram", self.policy))

    def test_agent_container_publish_from_main_allowed(self):
        allowed, _ = self._check(action="container-publish",
                                 ref="refs/heads/main")
        self.assertTrue(allowed)

    def test_agent_container_publish_from_pr_denied(self):
        allowed, reason = self._check(action="container-publish",
                                      ref="refs/pull/1")
        self.assertFalse(allowed)
        self.assertIn("main", reason)

    def test_agent_production_deploy_denied(self):
        allowed, _ = self._check(action="production-deploy")
        self.assertFalse(allowed)

    def test_agent_deploy_to_production_env_denied(self):
        allowed, reason = self._check(action="deploy", env="production")
        self.assertFalse(allowed)
        self.assertIn("staging", reason)

    def test_agent_deploy_to_staging_allowed(self):
        allowed, _ = self._check(action="deploy", env="staging")
        self.assertTrue(allowed)

    def test_human_production_deploy_allowed(self):
        allowed, _ = self._check(action="production-deploy",
                                 requested_by="vikram")
        self.assertTrue(allowed)

    def test_unknown_action_denied_for_agents(self):
        allowed, _ = self._check(action="rm-rf-everything")
        self.assertFalse(allowed)

    def test_cli_exit_codes(self):
        self.assertEqual(
            policy_check.main(["--action", "container-publish",
                               "--requested-by", "claude",
                               "--ref", "refs/heads/main"]), 0)
        self.assertEqual(
            policy_check.main(["--action", "container-publish",
                               "--requested-by", "claude",
                               "--ref", "refs/pull/1"]), 1)


if __name__ == "__main__":
    unittest.main()
