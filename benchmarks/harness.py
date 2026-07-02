#!/usr/bin/env python3
"""Load harness — drives chat completions through the router and writes one
CSV row per request to benchmarks/raw/. Every latency/cost number shown on
the devboard or in docs must trace to a CSV this harness wrote; SLO-AUDITOR
re-runs these exact commands.

Stdlib-only, deterministic prompt set (seeded), threads for concurrency.

Examples:
  # 60s steady load at concurrency 8:
  python3 benchmarks/harness.py --router http://localhost:8090 \
      --model qwen3-8b --concurrency 8 --duration 60 --label steady-c8

  # goodput sweep (writes one CSV per step + goodput curve points):
  python3 benchmarks/harness.py --router http://localhost:8090 \
      --model qwen3-8b --sweep 1,2,4,8,16,24 --duration 30 --label sweep

Then: python3 benchmarks/summarize.py benchmarks/raw/<label>-*.csv
"""

import argparse
import csv
import json
import os
import random
import threading
import time
import urllib.error
import urllib.request

CSV_FIELDS = [
    "ts", "req_id", "label", "concurrency", "model", "replica", "provider",
    "http_status", "client_ttft_ms", "client_decode_ms", "client_total_ms",
    "sse_chunks", "server_ttft_ms", "server_decode_ms", "tpot_ms",
    "prompt_tokens", "completion_tokens", "est_cost_usd", "cache",
    "route_reason",
]

PROMPTS = [
    "Summarize the tradeoffs between prefill and decode in LLM serving.",
    "Explain KV-cache reuse to a new engineer in three sentences.",
    "What makes cold starts expensive for GPU inference?",
    "Draft a one-line status update: latency SLO met, costs down.",
    "List three causes of tail latency in token streaming.",
    "Why do voice agents need tight TPOT guarantees?",
    "Describe canary releases for model weights briefly.",
    "How does prefix affinity routing reduce prefill cost?",
]


def one_request(router, model, label, conc, seq, rng, max_tokens, timeout):
    prompt = f"{rng.choice(PROMPTS)} (variant {seq})"
    body = json.dumps({
        "model": model, "max_tokens": max_tokens, "stream": True,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        f"{router}/v1/chat/completions?model={model}", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    row = {"ts": round(time.time(), 3), "req_id": f"{label}-{seq}",
           "label": label, "concurrency": conc, "model": model}
    t0 = time.monotonic()
    first = None
    last = None
    chunks = 0
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            h = resp.headers
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if line.startswith("data:") and line != "data: [DONE]":
                    last = time.monotonic()
                    if first is None:
                        first = last
                    chunks += 1
            t_end = time.monotonic()
            row.update({
                "http_status": resp.status,
                "replica": h.get("X-Replica", ""),
                "provider": h.get("X-Backend", ""),
                "server_ttft_ms": h.get("X-TTFT-Ms", ""),
                "server_decode_ms": h.get("X-Decode-Ms", ""),
                "prompt_tokens": h.get("X-Prompt-Tokens", ""),
                "completion_tokens": h.get("X-Completion-Tokens", ""),
                "est_cost_usd": h.get("X-Est-Cost", ""),
                "cache": h.get("X-Cache", ""),
                "route_reason": h.get("X-Route-Reason", ""),
            })
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        status = getattr(exc, "code", 0)
        row.update({"http_status": status or 0, "replica": "", "provider": "",
                    "server_ttft_ms": "", "server_decode_ms": "",
                    "prompt_tokens": "", "completion_tokens": "",
                    "est_cost_usd": "", "cache": "", "route_reason": ""})
        row["client_ttft_ms"] = ""
        row["client_decode_ms"] = ""
        row["client_total_ms"] = round((time.monotonic() - t0) * 1000, 1)
        row["sse_chunks"] = 0
        row["tpot_ms"] = ""
        return row
    row["client_ttft_ms"] = round(((first or t_end) - t0) * 1000, 1)
    row["client_decode_ms"] = round((last - first) * 1000, 1) if first else ""
    row["client_total_ms"] = round((t_end - t0) * 1000, 1)
    row["sse_chunks"] = chunks
    # server-reported when available (sim/pool proxy); client-measured
    # otherwise (live streams): decode time over emitted tokens
    completion = int(row["completion_tokens"] or 0) or chunks
    row["completion_tokens"] = completion
    decode = float(row["server_decode_ms"] or 0.0) or \
        float(row["client_decode_ms"] or 0.0)
    row["tpot_ms"] = round(decode / completion, 2) if completion else ""
    return row


def run_step(router, model, label, conc, duration, max_tokens, timeout,
             writer, lock, seed):
    stop_at = time.monotonic() + duration
    counter = {"n": 0}

    def worker(wid):
        rng = random.Random(seed + wid)
        streak = 0
        while time.monotonic() < stop_at:
            with lock:
                counter["n"] += 1
                seq = counter["n"]
            row = one_request(router, model, label, conc, seq, rng,
                              max_tokens, timeout)
            with lock:
                writer.writerow(row)
            # back off on failures instead of hot-looping a dead router;
            # give up after 10 consecutive errors
            if str(row.get("http_status")) in ("0", "502", "503"):
                streak += 1
                if streak >= 10:
                    print(f"worker {wid}: 10 consecutive errors — aborting")
                    return
                time.sleep(min(2.0, 0.2 * streak))
            else:
                streak = 0

    threads = [threading.Thread(target=worker, args=(w,), daemon=True)
               for w in range(conc)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return counter["n"]


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--router", default="http://localhost:8090")
    p.add_argument("--model", default="qwen3-8b")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--sweep", help="comma-separated concurrency steps")
    p.add_argument("--duration", type=float, default=30.0,
                   help="seconds per step")
    p.add_argument("--max-tokens", type=int, default=48)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--label", default="run")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--out-dir", default="benchmarks/raw")
    args = p.parse_args(argv)

    os.makedirs(args.out_dir, exist_ok=True)
    steps = ([int(s) for s in args.sweep.split(",")] if args.sweep
             else [args.concurrency])
    stamp = time.strftime("%Y%m%d-%H%M%S")
    lock = threading.Lock()
    for conc in steps:
        path = os.path.join(args.out_dir,
                            f"{args.label}-c{conc}-{stamp}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            n = run_step(args.router, args.model, args.label, conc,
                         args.duration, args.max_tokens, args.timeout,
                         writer, lock, args.seed)
        print(f"c={conc}: {n} requests -> {path}")


if __name__ == "__main__":
    main()
