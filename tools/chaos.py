#!/usr/bin/env python3
"""chaos.py — CHAOS-AGENT's fault-injection arsenal. Stdlib-only.

Every attack the eval agent runs goes through this tool (it is the audit
trail). Sim targets are the local pool proxies; live targets delegate to
deploy/ scripts so keys/budget guards stay in one place.

Attacks:
  inject      add latency and/or a 5xx rate to a pool (needs CHAOS_ENABLED=1
              on that pool instance)
  clear       remove all injection from a pool
  status      show a pool's current injection
  kill        kill the local pool process listening on a port (sim pod kill);
              --runpod delegates to deploy/runpod/pod.py down (REAL teardown)
  exhaust     saturate the router past a concurrency target via the bench
              harness (writes CSVs like any run — evidence included)
  deactivate-baseten
              delegates to deploy/baseten/manage.py deactivate (REAL)
  bad-release not implemented until F5 wires live canary control — the
              release engine must exist before we can push a bad version

Examples:
  python3 tools/chaos.py inject --target http://localhost:8102 --latency-ms 500
  python3 tools/chaos.py inject --target http://localhost:8102 --error-rate 0.5
  python3 tools/chaos.py clear  --target http://localhost:8102
  python3 tools/chaos.py kill --port 8102 --yes
  python3 tools/chaos.py exhaust --router http://localhost:8090 --concurrency 32
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _post(url, body):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"POST {url} -> HTTP {e.code} "
                 "(is the pool running with CHAOS_ENABLED=1?)")
    except urllib.error.URLError as e:
        sys.exit(f"POST {url} -> {e.reason}")


def cmd_inject(args):
    out = _post(f"{args.target}/chaos",
                {"latency_ms": args.latency_ms, "error_rate": args.error_rate})
    print(f"injected on {args.target}: {out}")


def cmd_clear(args):
    out = _post(f"{args.target}/chaos", {"latency_ms": 0, "error_rate": 0})
    print(f"cleared on {args.target}: {out}")


def cmd_status(args):
    with urllib.request.urlopen(f"{args.target}/chaos", timeout=5) as resp:
        print(resp.read().decode())


def cmd_kill(args):
    if args.runpod:
        os.execv(sys.executable,
                 [sys.executable, os.path.join(REPO, "deploy/runpod/pod.py"),
                  "down"] + (["--yes"] if args.yes else []))
    out = subprocess.run(["lsof", "-ti", f":{args.port}"],
                         capture_output=True, text=True)
    pids = [int(p) for p in out.stdout.split()]
    if not pids:
        sys.exit(f"nothing listening on :{args.port}")
    print(f"about to SIGKILL pid(s) {pids} on :{args.port}")
    if not args.yes:
        sys.exit("killing a pool requires --yes")
    for pid in pids:
        os.kill(pid, signal.SIGKILL)
    print(f"killed — pool on :{args.port} is gone; watch the router eject it")


def cmd_exhaust(args):
    os.execv(sys.executable,
             [sys.executable, os.path.join(REPO, "benchmarks/harness.py"),
              "--router", args.router, "--model", args.model,
              "--concurrency", str(args.concurrency),
              "--duration", str(args.duration),
              "--label", f"chaos-exhaust-c{args.concurrency}"])


def cmd_deactivate_baseten(args):
    argv = [sys.executable, os.path.join(REPO, "deploy/baseten/manage.py"),
            "deactivate", args.deployment_id, "--model-id", args.model_id]
    if args.yes:
        argv.append("--yes")
    os.execv(sys.executable, argv)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("inject")
    i.add_argument("--target", required=True)
    i.add_argument("--latency-ms", type=float, default=0.0)
    i.add_argument("--error-rate", type=float, default=0.0)
    i.set_defaults(fn=cmd_inject)

    for name, fn in (("clear", cmd_clear), ("status", cmd_status)):
        c = sub.add_parser(name)
        c.add_argument("--target", required=True)
        c.set_defaults(fn=fn)

    k = sub.add_parser("kill")
    k.add_argument("--port", type=int)
    k.add_argument("--runpod", action="store_true")
    k.add_argument("--yes", action="store_true")
    k.set_defaults(fn=cmd_kill)

    e = sub.add_parser("exhaust")
    e.add_argument("--router", default="http://localhost:8090")
    e.add_argument("--model", default="qwen3-8b")
    e.add_argument("--concurrency", type=int, default=32)
    e.add_argument("--duration", type=float, default=20.0)
    e.set_defaults(fn=cmd_exhaust)

    d = sub.add_parser("deactivate-baseten")
    d.add_argument("deployment_id")
    d.add_argument("--model-id", required=True)
    d.add_argument("--yes", action="store_true")
    d.set_defaults(fn=cmd_deactivate_baseten)

    b = sub.add_parser("bad-release")
    b.set_defaults(fn=lambda a: sys.exit(
        "bad-release arms in F5 when the release engine takes live pushes"))

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
