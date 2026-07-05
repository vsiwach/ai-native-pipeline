#!/usr/bin/env python3
"""Generate replay narration from a recorded console trace.

Captions are DERIVED from the recorded events — state transitions the
audience would otherwise have to infer (pod ready, load running, cert
verdict, promote/rollback) — never invented. Output: [{t, text}, ...].

Usage:
  python3 tools/replay_captions.py \
      --trace vercel-deploy/replay/console-trace.jsonl \
      --out vercel-deploy/replay/captions.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    caps: list[dict] = []

    def say(t: float, text: str):
        if not caps or caps[-1]["text"] != text:
            caps.append({"t": round(t, 1), "text": text})

    pods_seen: dict[str, dict] = {}
    jobs_seen: dict[str, int | None] = {}
    load_running = False
    serving = None

    for line in Path(args.trace).read_text().splitlines():
        ev = json.loads(line)
        t, src, d = ev["t"], ev["src"], ev["data"]
        if src == "meta":
            say(t, "Recorded real run — every number below was measured, "
                   "none simulated for display.")
        elif src == "gpu" and d.get("enabled"):
            for p in d.get("pods", []):
                prev = pods_seen.get(p["id"])
                if prev is None:
                    say(t, f"GPU pool {p['kind'].upper()} rented at "
                           f"${p['usd_hr']}/hr ({p.get('gpu') or 'GPU'}) — "
                           "billing started, serving not yet up.")
                elif not prev["ready"] and p["ready"]:
                    say(t, f"{p['kind'].upper()} is READY — MAX is serving "
                           "the model; the candidate route can adopt it.")
                pods_seen[p["id"]] = p
            gone = set(pods_seen) - {p["id"] for p in d.get("pods", [])}
            for pid in gone:
                k = pods_seen.pop(pid)["kind"].upper()
                say(t, f"{k} pod terminated from the console — the ledger "
                       "entry closes; per-second billing stops.")
            for name, job in (d.get("jobs") or {}).items():
                rc = job.get("rc")
                if name not in jobs_seen:
                    say(t, {"bench": "Bench started: real streamed traffic "
                                     "against the pool — $/Mtok is derived "
                                     "from measured tokens/sec at the "
                                     "declared $/hr.",
                            "certify": "Certifying: grounding + rubric "
                                       "parity on the shadow log, p99 SLO "
                                       "from the bench report, ed25519 "
                                       "signature."}.get(name, name))
                elif jobs_seen.get(name) is None and rc is not None:
                    tail = " ".join(job.get("tail") or [])[:120]
                    if name == "certify":
                        verdict = ("PASS — promotion unlocked"
                                   if rc == 0 else "HOLD — the gate refused")
                        say(t, f"Certificate: {verdict}. ({tail})")
                    else:
                        say(t, f"Bench done: {tail}")
                jobs_seen[name] = rc
        elif src == "loadgen":
            if d.get("running") and not load_running:
                say(t, "Synthetic load started: the 12 eval questions "
                       "replay through the router; the primary answers the "
                       "client while every request is mirrored to the "
                       "candidate — the shadow log is the cert evidence.")
            if load_running and not d.get("running") and d.get("sent"):
                say(t, f"Load run finished: {d['sent']} sent, "
                       f"{d.get('errors', 0)} errors.")
            load_running = bool(d.get("running"))
        elif src == "costs":
            s = (d.get("routes") or {}).get("docs-assist", {}).get("serving")
            if serving and s and s != serving:
                if "candidate" in s:
                    say(t, "PROMOTED — the route's primary swapped to the "
                           "GPU candidate; clients now get its answers.")
                else:
                    say(t, "ROLLED BACK — the incumbent serves again; the "
                           "release engine recorded both transitions.")
            serving = s or serving

    Path(args.out).write_text(json.dumps(caps, indent=1))
    print(f"{len(caps)} captions -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
