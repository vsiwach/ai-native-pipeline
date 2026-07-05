#!/usr/bin/env python3
"""Record the console's data plane — every source demo.html polls — into a
timestamped JSONL trace. The REPLAY tab plays these back verbatim, so when
RunPod (or any provider) is flaky during a live demo, the audience still
sees a REAL recorded run, never a fabrication (repo replay philosophy).

Usage:
  python3 tools/record_console.py --router http://127.0.0.1:8114 \
      --interval 2 --out demo-artifacts/gpu-20260705/console-trace.jsonl
Stop with Ctrl-C / kill; each line: {"t": <s since start>, "src": ..., "data": ...}.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.request

SOURCES = {
    "costs": "/v1/costs",
    "gpu": "/v1/dev/gpu",
    "loadgen": "/v1/dev/loadgen",
    "shadow": "/v1/routes/docs-assist/shadow-stats",
}


def snap(router: str, path: str):
    try:
        with urllib.request.urlopen(f"{router}{path}", timeout=15) as r:
            return json.loads(r.read())
    except Exception as exc:  # noqa: BLE001 — outages are part of the story
        return {"_error": str(exc)[:120]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--router", default="http://127.0.0.1:8114")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    t0 = time.time()
    last: dict[str, str] = {}
    with open(args.out, "a") as f:
        f.write(json.dumps({"t": 0.0, "src": "meta", "data": {
            "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "router": args.router,
            "note": "recorded real console data plane; no fabricated values",
        }}) + "\n")
        f.flush()
        while True:
            for src, path in SOURCES.items():
                data = snap(args.router, path)
                blob = json.dumps(data, sort_keys=True)
                if last.get(src) == blob:
                    continue          # only state CHANGES land in the trace
                last[src] = blob
                f.write(json.dumps({"t": round(time.time() - t0, 1),
                                    "src": src, "data": data}) + "\n")
                f.flush()
            time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
