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
  drill       SCRIPTED incident drill with measured MTTR: start load, inject
              a fault through the router, watch the incident agent detect →
              quarantine → probe → reinstate → resolve, and write the whole
              timeline + MTTR to benchmarks/raw/ (the evidence chain)
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
  python3 tools/chaos.py drill --scenario latency --router http://localhost:8090
  python3 tools/chaos.py drill --suite --model glm-4.7 --latency-ms 2500
"""

import argparse
import csv
import json
import os
import signal
import subprocess
import sys
import threading
import time
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


def _chaos_surface(args):
    """Two audited injection surfaces:
    pool-direct (--target http://pool:PORT -> POST {target}/chaos) or
    router dev  (--router http://router:PORT --pool-id X ->
                 POST {router}/v1/dev/chaos with pool_id) — same surface the
    incident agent watches, so router-mode is preferred for invariant attacks.
    """
    if getattr(args, "pool_id", None):
        if not getattr(args, "router", None):
            sys.exit("--pool-id requires --router")
        return f"{args.router}/v1/dev/chaos", {"pool_id": args.pool_id}
    if not args.target:
        sys.exit("need --target (pool-direct) or --router + --pool-id")
    return f"{args.target}/chaos", {}


def cmd_inject(args):
    url, extra = _chaos_surface(args)
    out = _post(url, {**extra, "latency_ms": args.latency_ms,
                      "error_rate": args.error_rate})
    print(f"injected on {url}"
          f"{' pool=' + args.pool_id if extra else ''}: {out}")


def cmd_clear(args):
    url, extra = _chaos_surface(args)
    out = _post(url, {**extra, "latency_ms": 0, "error_rate": 0})
    print(f"cleared on {url}"
          f"{' pool=' + args.pool_id if extra else ''}: {out}")


def cmd_status(args):
    url = (f"{args.router}/v1/dev/chaos" if getattr(args, "pool_id", None)
           or not args.target else f"{args.target}/chaos")
    with urllib.request.urlopen(url, timeout=5) as resp:
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


# ---------------------------------------------------------------------------
# drill — scripted fault → agent-resolved incident → measured MTTR evidence
# ---------------------------------------------------------------------------

SCENARIOS = {
    # magnitudes must clearly breach the watched tier's SLO; --latency-ms /
    # --error-rate override per run (realtime tier: TTFT SLO 500ms)
    "latency": {"latency_ms": 600.0, "error_rate": 0.0},
    "errors":  {"latency_ms": 0.0,   "error_rate": 0.9},
    "combo":   {"latency_ms": 600.0, "error_rate": 0.5},
}


def _get_json(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read())


class _Load(threading.Thread):
    """Steady streaming chat load through the router — the traffic whose
    breach samples the incident agent detects. Streaming so injected latency
    lands in the ROUTER-measured TTFT (non-stream TTFT comes from backend
    headers, which chaos sleeps don't touch)."""

    def __init__(self, router, model, rps=3.0):
        super().__init__(daemon=True)
        self.router, self.model, self.period = router, model, 1.0 / rps
        self.stop = threading.Event()
        self.sent = 0
        self.errors = 0

    def run(self):
        while not self.stop.is_set():
            # vary the prompt so prefix-affinity spreads load across ALL
            # replicas — identical prompts would pin every request to one
            # replica and chaos on the other pool would go undetected
            body = json.dumps({"model": self.model, "max_tokens": 8,
                               "stream": True,
                               "messages": [{"role": "user",
                                             "content": f"drill traffic "
                                                        f"{self.sent}"}]
                               }).encode()
            req = urllib.request.Request(
                f"{self.router}/v1/chat/completions", data=body,
                headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    for _ in resp:  # drain the stream
                        pass
                self.sent += 1
            except (urllib.error.URLError, OSError):
                self.sent += 1
                self.errors += 1
            self.stop.wait(self.period)


def _drill_once(args, scenario: str) -> dict:
    router = args.router.rstrip("/")
    magnitudes = dict(SCENARIOS[scenario])
    if args.latency_ms is not None and magnitudes["latency_ms"]:
        magnitudes["latency_ms"] = args.latency_ms
    if args.error_rate is not None and magnitudes["error_rate"]:
        magnitudes["error_rate"] = args.error_rate

    caps = _get_json(f"{router}/v1/dev/chaos")["pools"]
    capable = [p["id"] for p in caps if p["capable"]]
    if not capable:
        sys.exit("no chaos-capable pools behind the router "
                 "(pools need CHAOS_ENABLED=1)")
    pool = args.pool_id or capable[0]
    if pool not in capable:
        sys.exit(f"pool {pool!r} is not chaos-capable (capable: {capable})")

    known = {i["id"] for i in _get_json(f"{router}/v1/incidents")}
    stamp = time.strftime("%Y%m%d-%H%M%S")
    timeline: list[tuple[float, str, str]] = []
    t0 = time.monotonic()

    def mark(event, detail=""):
        timeline.append((round(time.monotonic() - t0, 2), event, detail))
        print(f"  [{timeline[-1][0]:7.2f}s] {event:12s} {detail}")

    print(f"drill '{scenario}' → pool {pool} via {router} "
          f"(model {args.model})")
    load = _Load(router, args.model, rps=args.rps)
    load.start()
    mark("load_start", f"{args.rps} rps streaming, model={args.model}")
    time.sleep(args.warmup_s)   # healthy baseline samples first

    _post(f"{router}/v1/dev/chaos", {"pool_id": pool, **magnitudes})
    mark("inject", json.dumps(magnitudes))

    incident, detected_s, quarantined_s, cleared_s = None, None, None, None
    deadline = time.monotonic() + args.timeout_s
    try:
        while time.monotonic() < deadline:
            time.sleep(0.5)
            snap = _get_json(f"{router}/v1/incidents")
            if incident is None:
                # only incidents naming OUR target pool count — an unrelated
                # flap on another pool must not be scored as this drill
                fresh = [i for i in snap
                         if i["id"] not in known and pool in i["title"]]
                if fresh:
                    incident = fresh[-1]["id"]
                    detected_s = round(time.monotonic() - t0, 2)
                    mark("detected", f"{incident}: {fresh[-1]['title']}")
            if incident is not None:
                inc = next(i for i in snap if i["id"] == incident)
                acts = " | ".join(inc["actions"])
                if quarantined_s is None and "quarantined" in acts:
                    quarantined_s = round(time.monotonic() - t0, 2)
                    mark("quarantined", "traffic spilled to healthy pool")
                # lift the fault once the agent has contained it (or
                # immediately for uncontainable last-pool cases after hold_s)
                if cleared_s is None and (
                        quarantined_s is not None
                        or time.monotonic() - t0 > args.hold_s):
                    _post(f"{router}/v1/dev/chaos",
                          {"pool_id": pool, "latency_ms": 0, "error_rate": 0})
                    cleared_s = round(time.monotonic() - t0, 2)
                    mark("cleared", "fault removed — agent must now verify")
                if not inc["live"]:
                    mark("resolved", f"MTTR {inc['mttr_s']}s "
                                     f"(agent={inc['agent']})")
                    return _drill_record(args, scenario, pool, magnitudes,
                                         stamp, timeline, load, inc,
                                         detected_s, quarantined_s, cleared_s)
        mark("timeout", f"no resolution within {args.timeout_s}s — FAIL")
        return _drill_record(args, scenario, pool, magnitudes, stamp,
                             timeline, load, None, detected_s, quarantined_s,
                             cleared_s)
    finally:
        load.stop.set()
        if cleared_s is None:  # never leave a fault armed, on ANY exit path
            _post(f"{router}/v1/dev/chaos",
                  {"pool_id": pool, "latency_ms": 0, "error_rate": 0})


def _drill_record(args, scenario, pool, magnitudes, stamp, timeline, load,
                  inc, detected_s, quarantined_s, cleared_s) -> dict:
    raw_dir = os.path.join(REPO, "benchmarks", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    detail = os.path.join(raw_dir, f"chaos_drill_{scenario}_{stamp}.csv")
    with open(detail, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_rel_s", "event", "detail"])
        w.writerows(timeline)
    summary_path = os.path.join(raw_dir, "chaos_drills.csv")
    new = not os.path.exists(summary_path)
    row = {
        "stamp": stamp, "scenario": scenario, "pool": pool,
        "model": args.model, "latency_ms": magnitudes["latency_ms"],
        "error_rate": magnitudes["error_rate"],
        "agent": inc["agent"] if inc else "",
        "detected_s": detected_s, "quarantined_s": quarantined_s,
        "cleared_s": cleared_s,
        "mttr_s": inc["mttr_s"] if inc else "",
        "resolved": bool(inc), "requests": load.sent,
        "request_errors": load.errors,
    }
    with open(summary_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)
    print(f"  evidence: {os.path.relpath(detail, REPO)}  +  "
          f"{os.path.relpath(summary_path, REPO)}")
    return row


def cmd_drill(args):
    scenarios = list(SCENARIOS) if args.suite else [args.scenario]
    results = []
    for i, sc in enumerate(scenarios):
        if i:
            print(f"cooldown {args.cooldown_s}s (agent anti-flap window)…")
            time.sleep(args.cooldown_s)
        results.append(_drill_once(args, sc))
    failed = [r["scenario"] for r in results if not r["resolved"]]
    print("\nMTTR summary:")
    for r in results:
        status = f"{r['mttr_s']}s" if r["resolved"] else "UNRESOLVED"
        print(f"  {r['scenario']:8s} detect {r['detected_s']}s  "
              f"quarantine {r['quarantined_s']}s  mttr {status}")
    if failed:
        sys.exit(f"drill FAILED: unresolved scenarios: {failed}")


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
    i.add_argument("--target", help="pool base URL (pool-direct mode)")
    i.add_argument("--router", help="router base URL (router dev-chaos mode)")
    i.add_argument("--pool-id", help="pool id for router dev-chaos mode")
    i.add_argument("--latency-ms", type=float, default=0.0)
    i.add_argument("--error-rate", type=float, default=0.0)
    i.set_defaults(fn=cmd_inject)

    for name, fn in (("clear", cmd_clear), ("status", cmd_status)):
        c = sub.add_parser(name)
        c.add_argument("--target", help="pool base URL (pool-direct mode)")
        c.add_argument("--router", help="router base URL")
        c.add_argument("--pool-id", help="pool id for router dev-chaos mode")
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

    dr = sub.add_parser("drill", help="scripted incident drill with "
                                      "measured MTTR evidence")
    dr.add_argument("--router", default="http://localhost:8090")
    dr.add_argument("--scenario", choices=sorted(SCENARIOS),
                    default="latency")
    dr.add_argument("--suite", action="store_true",
                    help="run every scenario back to back")
    dr.add_argument("--pool-id", help="target pool (default: first "
                                      "chaos-capable pool)")
    dr.add_argument("--model", default="qwen3-8b",
                    help="model to load-test — must be the model the "
                         "incident agent watches (DEVBOARD_MODEL)")
    dr.add_argument("--latency-ms", type=float, default=None,
                    help="override scenario latency (must breach the "
                         "tier's TTFT SLO to be detectable)")
    dr.add_argument("--error-rate", type=float, default=None)
    dr.add_argument("--rps", type=float, default=1.0,
                    help="drill load; keep low against LIVE pools — hosted "
                         "Model APIs enforce request quotas, and tripping "
                         "them mid-drill poisons probe verification")
    dr.add_argument("--warmup-s", type=float, default=4.0)
    dr.add_argument("--hold-s", type=float, default=25.0,
                    help="clear the fault after this long even without "
                         "quarantine (last-pool cases)")
    dr.add_argument("--timeout-s", type=float, default=150.0)
    dr.add_argument("--cooldown-s", type=float, default=35.0,
                    help="gap between suite scenarios (> agent cooldown)")
    dr.set_defaults(fn=cmd_drill)

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
