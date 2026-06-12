"""Tests for the MCP server's request handling (no subprocess/terraform)."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import mcp_server  # noqa: E402


def call(method, params=None, rid=1):
    return mcp_server.handle(
        {"jsonrpc": "2.0", "id": rid, "method": method,
         "params": params or {}})


class McpServerTest(unittest.TestCase):
    def test_initialize(self):
        resp = call("initialize")
        self.assertEqual(resp["result"]["serverInfo"]["name"],
                         "ai-native-pipeline")

    def test_tools_list_exposes_both_tools(self):
        names = {t["name"] for t in call("tools/list")["result"]["tools"]}
        self.assertEqual(names, {"get_cloud_endpoints", "run_terraform_plan"})

    def test_get_cloud_endpoints_reads_policy(self):
        resp = call("tools/call", {"name": "get_cloud_endpoints",
                                   "arguments": {}})
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("house-price-reg", payload["endpoints"])

    def test_unknown_tool_is_error(self):
        resp = call("tools/call", {"name": "rm_rf", "arguments": {}})
        self.assertTrue(resp["result"]["isError"])

    def test_unknown_environment_refused(self):
        result = mcp_server.run_terraform_plan({"environment": "production"})
        self.assertIn("error", result)

    def test_notifications_get_no_response(self):
        resp = mcp_server.handle({"jsonrpc": "2.0",
                                  "method": "notifications/initialized"})
        self.assertIsNone(resp)


if __name__ == "__main__":
    unittest.main()
