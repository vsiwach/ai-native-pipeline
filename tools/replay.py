#!/usr/bin/env python3
"""Traffic replayer — sends eval questions through the router as live traffic.

Drives the shadow phase: each question goes to the route's PRIMARY backend
(the router mirrors to the candidate). Timed replay with jitter so the
console's live panels move like real traffic.

Usage:
  python3 tools/replay.py --router http://localhost:8600 --route docs-assist \
      --evals evals/docs_qa.jsonl --rps 0.5 --loop 3
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
from pathlib import Path

import httpx


async def main_async(args):
    items = [json.loads(l) for l in Path(args.evals).read_text().splitlines() if l.strip()]
    async with httpx.AsyncClient(timeout=120) as client:
        for loop_n in range(args.loop):
            for it in items:
                body = {"messages": [{"role": "user", "content": it["question"]}],
                        "max_tokens": 300}
                try:
                    r = await client.post(
                        f"{args.router}/v1/chat/completions",
                        params={"model": args.route}, json=body)
                    print(f"[{loop_n}] {r.status_code} {it['question'][:60]}")
                except Exception as e:  # noqa: BLE001
                    print(f"[{loop_n}] ERR {e}")
                await asyncio.sleep(random.uniform(0.5, 1.5) / args.rps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--router", default="http://localhost:8600")
    ap.add_argument("--route", default="docs-assist")
    ap.add_argument("--evals", default="evals/docs_qa.jsonl")
    ap.add_argument("--rps", type=float, default=0.5)
    ap.add_argument("--loop", type=int, default=1)
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
