#!/usr/bin/env python3
"""Baseten management CLI — status, autoscaling, activate/promote, logs.

Stdlib-only. Auth: BASETEN_API_KEY env var (never a file, never an argument).
Nothing here runs without the key; every mutating call prints the request it
is about to make and requires --yes.

Endpoints follow the Baseten management API (api.baseten.co). Paths were
written from docs knowledge and MUST be smoke-tested in the first live
session; every mismatch found becomes a docs/FRICTION_LOG.md entry.

Usage:
  python3 deploy/baseten/manage.py status                      # all models + deployments
  python3 deploy/baseten/manage.py status --model-id <id>
  python3 deploy/baseten/manage.py autoscaling <deployment-id> \
      --min 0 --max 3 --concurrency 8 [--model-id <id>] --yes
  python3 deploy/baseten/manage.py activate   <deployment-id> --model-id <id> --yes
  python3 deploy/baseten/manage.py deactivate <deployment-id> --model-id <id> --yes
  python3 deploy/baseten/manage.py promote    <deployment-id> --model-id <id> --yes
  python3 deploy/baseten/manage.py logs <deployment-id> --model-id <id>
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.baseten.co/v1"


def _key():
    key = os.environ.get("BASETEN_API_KEY")
    if not key:
        sys.exit("BASETEN_API_KEY not set — export it (env var only, per mission rules).")
    return key


def _call(method, path, body=None):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Api-Key {_key()}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        sys.exit(f"{method} {path} -> HTTP {e.code}: {detail}")


def _confirm(args, description):
    print(f"about to: {description}")
    if not args.yes:
        sys.exit("mutating call requires --yes")


def cmd_status(args):
    if args.model_id:
        out = _call("GET", f"/models/{args.model_id}/deployments")
    else:
        out = _call("GET", "/models")
    print(json.dumps(out, indent=2))


def cmd_autoscaling(args):
    body = {
        "min_replica": args.min,
        "max_replica": args.max,
        "autoscaling_window": args.window,
        "concurrency_target": args.concurrency,
        "scale_down_delay": args.scale_down_delay,
    }
    body = {k: v for k, v in body.items() if v is not None}
    path = f"/models/{args.model_id}/deployments/{args.deployment_id}/autoscaling_settings"
    _confirm(args, f"PATCH {path} {body}")
    print(json.dumps(_call("PATCH", path, body), indent=2))


def _simple_action(args, action):
    path = f"/models/{args.model_id}/deployments/{args.deployment_id}/{action}"
    _confirm(args, f"POST {path}")
    print(json.dumps(_call("POST", path, {}), indent=2))


def cmd_logs(args):
    # Deployment logs endpoint; verify exact path live (friction candidate).
    path = f"/models/{args.model_id}/deployments/{args.deployment_id}/logs"
    print(json.dumps(_call("GET", path), indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status")
    s.add_argument("--model-id")
    s.set_defaults(fn=cmd_status)

    a = sub.add_parser("autoscaling")
    a.add_argument("deployment_id")
    a.add_argument("--model-id", required=True)
    a.add_argument("--min", type=int)
    a.add_argument("--max", type=int)
    a.add_argument("--concurrency", type=int)
    a.add_argument("--window", type=int)
    a.add_argument("--scale-down-delay", type=int)
    a.add_argument("--yes", action="store_true")
    a.set_defaults(fn=cmd_autoscaling)

    for action in ("activate", "deactivate", "promote"):
        c = sub.add_parser(action)
        c.add_argument("deployment_id")
        c.add_argument("--model-id", required=True)
        c.add_argument("--yes", action="store_true")
        c.set_defaults(fn=lambda args, _a=action: _simple_action(args, _a))

    l = sub.add_parser("logs")
    l.add_argument("deployment_id")
    l.add_argument("--model-id", required=True)
    l.set_defaults(fn=cmd_logs)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
