#!/usr/bin/env python3
"""RunPod vLLM pod lifecycle — provision / status / teardown, with budget guard.

Stdlib-only. Auth: RUNPOD_API_KEY env var only. One pod, one GPU (L4 or A10,
~$0.30-0.60/hr), running the official vLLM OpenAI-compatible server with a
Qwen3-8B-class model — the mission's second pool.

BUDGET GUARD: the mission caps total cloud spend at $40. Every `up` appends to
deploy/runpod/spend-ledger.json (start ts, $/hr); `down` closes the entry.
`up` aborts if (spent so far) + (requested hours estimate) projects past the
cap. `status` shows the running total. The ledger is committed — it is part of
the cost story.

Usage:
  python3 deploy/runpod/pod.py up   [--gpu "NVIDIA L4"] [--model Qwen/Qwen3-8B] \
      [--est-hours 2] [--max-hourly 0.60] --yes
  python3 deploy/runpod/pod.py status
  python3 deploy/runpod/pod.py down --yes
  python3 deploy/runpod/pod.py budget

Endpoint paths follow RunPod's REST API (rest.runpod.io/v1); verify on first
live run — mismatches become docs/FRICTION_LOG.md entries.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://rest.runpod.io/v1"
LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spend-ledger.json")
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pod-state.json")
BUDGET_CAP_USD = 40.0


def _key():
    key = os.environ.get("RUNPOD_API_KEY")
    if not key:
        sys.exit("RUNPOD_API_KEY not set — export it (env var only, per mission rules).")
    return key


def _call(method, path, body=None):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        sys.exit(f"{method} {path} -> HTTP {e.code}: {detail}")


# ---- budget ledger ---------------------------------------------------------

def _ledger():
    if os.path.exists(LEDGER):
        with open(LEDGER) as f:
            return json.load(f)
    return {"cap_usd": BUDGET_CAP_USD, "entries": []}


def _save_ledger(led):
    tmp = LEDGER + ".tmp"
    with open(tmp, "w") as f:
        json.dump(led, f, indent=2)
    os.replace(tmp, LEDGER)


def _spent(led):
    total = 0.0
    now = time.time()
    for e in led["entries"]:
        end = e.get("end_ts") or now
        total += (end - e["start_ts"]) / 3600.0 * e["usd_per_hr"]
    return total


def cmd_budget(_args):
    led = _ledger()
    spent = _spent(led)
    print(f"cap ${led['cap_usd']:.2f} · spent ${spent:.2f} · remaining ${led['cap_usd']-spent:.2f}")
    for e in led["entries"]:
        state = "OPEN" if not e.get("end_ts") else "closed"
        print(f"  {e['what']} · ${e['usd_per_hr']}/hr · {state}")


# ---- pod lifecycle ---------------------------------------------------------

def cmd_up(args):
    led = _ledger()
    spent = _spent(led)
    projected = spent + args.est_hours * args.max_hourly
    if projected > led["cap_usd"]:
        sys.exit(
            f"BUDGET GUARD: spent ${spent:.2f} + {args.est_hours}h*${args.max_hourly}/hr "
            f"projects ${projected:.2f} > cap ${led['cap_usd']:.2f}. Aborting."
        )
    if os.path.exists(STATE):
        sys.exit(f"pod state file exists ({STATE}) — one pod only; run `down` first.")

    body = {
        "name": "ai-native-vllm-pool",
        # pinned by default: an unpinned :latest means every fresh host
        # cold-pulls whatever was published today — which presents as
        # "rented, runtime:null" while billing (2026-07-02: four pods stuck)
        "imageName": args.image,
        "gpuTypeIds": [args.gpu],
        "gpuCount": 1,
        "cloudType": args.cloud,
        "containerDiskInGb": args.disk,
        "volumeInGb": 0,
        "ports": ["8000/http"],
        # vllm/vllm-openai has an ENTRYPOINT (the OpenAI api_server); the REST
        # API's field is `dockerStartCmd` (array), appended as the container
        # args. Small context to fit a 24GB card safely.
        "dockerStartCmd": [
            "--model", args.model,
            "--max-model-len", str(args.max_model_len),
            "--gpu-memory-utilization", "0.92",
            "--disable-log-requests",
        ],
    }
    if args.dtype:  # pre-Ampere GPUs (T4) can't run bf16 — pass --dtype half
        body["dockerStartCmd"] += ["--dtype", args.dtype]
    if os.environ.get("HF_TOKEN"):
        body["env"] = {"HF_TOKEN": os.environ["HF_TOKEN"]}
    print(f"about to create pod: gpu={args.gpu} model={args.model} "
          f"(≤${args.max_hourly}/hr, est {args.est_hours}h, projected total ${projected:.2f})")
    if not args.yes:
        sys.exit("provisioning costs money — requires --yes")

    out = _call("POST", "/pods", body)
    pod_id = out.get("id") or out.get("podId")
    if not pod_id:
        sys.exit(f"no pod id in response: {json.dumps(out)[:400]}")
    with open(STATE, "w") as f:
        json.dump({"pod_id": pod_id, "created": time.time()}, f)
    led["entries"].append({
        "what": f"runpod {args.gpu} pod {pod_id}",
        "start_ts": time.time(),
        "usd_per_hr": args.max_hourly,
        "end_ts": None,
    })
    _save_ledger(led)
    print(json.dumps(out, indent=2))
    print(f"\npod {pod_id} creating. OpenAI base URL once ready: "
          f"https://{pod_id}-8000.proxy.runpod.net/v1")


def cmd_status(_args):
    if not os.path.exists(STATE):
        print("no pod (state file absent)")
        cmd_budget(_args)
        return
    with open(STATE) as f:
        pod_id = json.load(f)["pod_id"]
    print(json.dumps(_call("GET", f"/pods/{pod_id}"), indent=2))
    cmd_budget(_args)


def cmd_down(args):
    if not os.path.exists(STATE):
        sys.exit("no pod state file — nothing to tear down")
    with open(STATE) as f:
        pod_id = json.load(f)["pod_id"]
    print(f"about to TERMINATE pod {pod_id}")
    if not args.yes:
        sys.exit("teardown requires --yes")
    _call("DELETE", f"/pods/{pod_id}")
    led = _ledger()
    for e in led["entries"]:
        if pod_id in e["what"] and not e.get("end_ts"):
            e["end_ts"] = time.time()
    _save_ledger(led)
    os.remove(STATE)
    print(f"pod {pod_id} terminated; ledger closed. ", end="")
    cmd_budget(args)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    u = sub.add_parser("up")
    u.add_argument("--gpu", default="NVIDIA GeForce RTX 4090")
    u.add_argument("--model", default="Qwen/Qwen3-8B")
    u.add_argument("--max-model-len", type=int, default=4096)
    u.add_argument("--cloud", default="SECURE", choices=["SECURE", "COMMUNITY"])
    u.add_argument("--disk", type=int, default=60)
    u.add_argument("--dtype", default=None,
                   help="vLLM --dtype override (e.g. 'half' for T4/pre-Ampere)")
    u.add_argument("--image", default="vllm/vllm-openai:v0.9.1",
                   help="pinned vLLM image (':latest' cold-pulls today's "
                        "publish on fresh hosts and can stall provisioning)")
    u.add_argument("--est-hours", type=float, default=3.0)
    u.add_argument("--max-hourly", type=float, default=0.70)
    u.add_argument("--yes", action="store_true")
    u.set_defaults(fn=cmd_up)

    for name, fn in (("status", cmd_status), ("budget", cmd_budget)):
        c = sub.add_parser(name)
        c.set_defaults(fn=fn)

    d = sub.add_parser("down")
    d.add_argument("--yes", action="store_true")
    d.set_defaults(fn=cmd_down)

    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
