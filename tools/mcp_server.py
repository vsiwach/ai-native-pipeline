#!/usr/bin/env python3
"""Minimal MCP server (stdio JSON-RPC) exposing pipeline tools to agents.

    claude mcp add pipeline -- python3 tools/mcp_server.py

Tools:
  get_cloud_endpoints  read routing-policy.yaml's endpoint map (read-only)
  run_terraform_plan   terraform plan in envs/<env> (read-only — agents may
                       ALWAYS plan; apply stays behind policy_check + CI)

Stdlib-only. Apply is intentionally absent: governance/agent-policy.yaml
gates `deploy`, and the only apply path is deploy-multicloud.yml.
"""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_endpoints  # noqa: E402  (reuse the endpoints parser)

REPO_ROOT = Path(__file__).resolve().parent.parent
PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "get_cloud_endpoints",
        "description": "Deployed endpoints per model from routing-policy.yaml "
                       "(provider + URL, as the router sees them).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_terraform_plan",
        "description": "Run a read-only `terraform plan` for an environment "
                       "with placeholder credentials. Never applies.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "environment": {"type": "string", "enum": ["staging"],
                                "default": "staging"},
            },
        },
    },
]


def get_cloud_endpoints(_args: dict) -> dict:
    policy = (REPO_ROOT / "routing-policy.yaml").read_text()
    return {"endpoints": sync_endpoints.parse_endpoints(policy)}


def run_terraform_plan(args: dict) -> dict:
    env = args.get("environment", "staging")
    env_dir = REPO_ROOT / "deploy" / "terraform" / "envs" / env
    if not env_dir.is_dir():
        return {"error": f"unknown environment '{env}'"}
    result = subprocess.run(
        ["terraform", f"-chdir={env_dir}", "plan",
         "-var-file=placeholder.tfvars", "-input=false", "-no-color"],
        capture_output=True, text=True, timeout=300,
    )
    output = (result.stdout + result.stderr).splitlines()
    return {"exit_code": result.returncode,
            "plan_tail": "\n".join(output[-60:])}


HANDLERS = {"get_cloud_endpoints": get_cloud_endpoints,
            "run_terraform_plan": run_terraform_plan}


def handle(request: dict) -> dict | None:
    method = request.get("method")
    rid = request.get("id")
    if method == "initialize":
        result = {"protocolVersion": PROTOCOL_VERSION,
                  "capabilities": {"tools": {}},
                  "serverInfo": {"name": "ai-native-pipeline",
                                 "version": "1.0"}}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = request.get("params", {})
        handler = HANDLERS.get(params.get("name"))
        if handler is None:
            result = {"content": [{"type": "text",
                                   "text": f"unknown tool {params.get('name')!r}"}],
                      "isError": True}
        else:
            payload = handler(params.get("arguments") or {})
            result = {"content": [{"type": "text",
                                   "text": json.dumps(payload, indent=2)}]}
    elif rid is None:  # notification — nothing to answer
        return None
    else:
        return {"jsonrpc": "2.0", "id": rid,
                "error": {"code": -32601, "message": f"unknown method {method}"}}
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        response = handle(json.loads(line))
        if response is not None:
            print(json.dumps(response), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
