#!/usr/bin/env python3
"""Gate agent actions against governance/agent-policy.yaml.

Usage:
    python3 tools/policy_check.py --action <action> [--requested-by <id>]
                                  [--ref <git-ref>] [--env <environment>]

Exit 0 = allowed, exit 1 = denied (reason on stderr). Humans pass unless an
action is denied outright; agents are subject to per-action restrictions.
Stdlib-only: CI and pre-push hooks call this before anything is installed.
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = REPO_ROOT / "governance" / "agent-policy.yaml"


def load_policy(path: Path = POLICY_PATH) -> dict:
    """Parse the two-level policy YAML (same constrained shape as the
    registry — see tools/devkit/registry.py for the rationale)."""
    policy: dict = {"agent_identities": [], "actions": {}}
    current_action: dict | None = None
    in_actions = False
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0:
            in_actions = stripped == "actions:"
            if stripped.startswith("agent_identities:"):
                value = stripped.partition(":")[2]
                policy["agent_identities"] = [
                    v.strip() for v in value.split(",") if v.strip()
                ]
        elif in_actions and indent == 2 and stripped.endswith(":"):
            current_action = {}
            policy["actions"][stripped[:-1].strip()] = current_action
        elif in_actions and indent >= 4 and current_action is not None:
            key, _, value = stripped.partition(":")
            current_action[key.strip()] = value.strip().strip("'\"")
    return policy


def is_agent(requested_by: str, policy: dict) -> bool:
    rb = requested_by.lower()
    return any(rb.startswith(ident.lower()) for ident in policy["agent_identities"])


def check(action: str, requested_by: str, ref: str | None,
          env: str | None, policy: dict) -> tuple[bool, str]:
    """Return (allowed, reason)."""
    rules = policy["actions"].get(action)
    if rules is None:
        return False, f"action '{action}' is not in the policy — denied by default"

    if not is_agent(requested_by, policy):
        return True, f"'{requested_by}' is human — policy does not restrict this action"

    if rules.get("agent_allowed", "false") != "true":
        return False, rules.get("reason", f"agents may not perform '{action}'")

    allowed_envs = rules.get("allowed_envs")
    if allowed_envs and env and env not in [e.strip() for e in allowed_envs.split(",")]:
        return False, (f"agents may only target envs [{allowed_envs}], "
                       f"requested '{env}'")

    allowed_refs = rules.get("allowed_refs")
    if allowed_refs and ref and ref not in [r.strip() for r in allowed_refs.split(",")]:
        return False, (f"{rules.get('reason', 'ref not allowed')} "
                       f"(allowed: [{allowed_refs}], requested: '{ref}')")

    return True, f"'{action}' permitted for agents under current policy"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", required=True)
    parser.add_argument("--requested-by", default="claude")
    parser.add_argument("--ref", default=None)
    parser.add_argument("--env", default=None)
    args = parser.parse_args(argv)

    policy = load_policy()
    allowed, reason = check(args.action, args.requested_by, args.ref,
                            args.env, policy)
    stream = sys.stdout if allowed else sys.stderr
    verdict = "ALLOWED" if allowed else "DENIED"
    print(f"policy_check: {verdict} — {reason}", file=stream)
    return 0 if allowed else 1


if __name__ == "__main__":
    sys.exit(main())
