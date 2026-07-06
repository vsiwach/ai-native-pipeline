#!/usr/bin/env python3
"""./dev bench — $/Mtok at fixed SLO against any OpenAI-compatible endpoint (PRD F0.2).

Measures, per pool, with real streamed traffic:
  TTFT  (time to first token, ms)      p50 / p95 / p99
  TPOT  (time per output token, ms)    p50 / p95 / p99
  output tokens/sec (aggregate)        -> $/Mtok = pool $/hr / (tok/s * 3600) * 1e6

Honesty rules baked in:
  - $/Mtok is derived ONLY from measured tok/s and the operator-declared
    pool price; both appear in the report.
  - The report embeds the exact request profile so anyone can rerun it.
  - SLO pass/fail is computed at p99, not average.

Usage:
  python3 tools/bench.py --base-url http://<pod>:8000/v1 \
      --model Qwen/Qwen2.5-14B-Instruct --pool-usd-hr 1.64 --pool-name a100-nvidia \
      --profile docs-agent --requests 60 --concurrency 6 \
      --slo-ttft-ms 800 --out bench-reports/a100.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

import httpx

PROFILES = {
    # (prompt tokens ~, max output tokens) — mirrors PRD F0.2's workload profiles
    "docs-agent": {"prompt_pad": 1800, "max_tokens": 300,
                   "note": "RAG context + question -> cited answer (decode-moderate)"},
    "coding-agent": {"prompt_pad": 3500, "max_tokens": 900,
                     "note": "long context, long generation (decode-heavy)"},
    "voice": {"prompt_pad": 300, "max_tokens": 80,
              "note": "short turns, latency-critical"},
}
QUESTION = "Summarize how KV-aware routing decides replica placement. Cite sources."


def pct(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(len(xs) * p / 100))], 1)


async def one(client, url, model, profile, api_key, ttfts, tpots, tok_counts):
    pad = "modular " * (PROFILES[profile]["prompt_pad"] // 2)
    body = {
        "model": model,
        "messages": [{"role": "system", "content": pad},
                     {"role": "user", "content": QUESTION}],
        "max_tokens": PROFILES[profile]["max_tokens"],
        "stream": True,
    }
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    t0 = time.perf_counter()
    first, n_tok, last = None, 0, t0
    async with client.stream("POST", f"{url}/chat/completions", json=body,
                             headers=headers) as r:
        async for line in r.aiter_lines():
            if not line.startswith("data:") or "[DONE]" in line:
                continue
            now = time.perf_counter()
            if first is None:
                first = now
            n_tok += 1
            last = now
    if first and n_tok > 1:
        ttfts.append((first - t0) * 1000)
        tpots.append((last - first) * 1000 / (n_tok - 1))
        tok_counts.append((n_tok, last - t0))


async def bench(args):
    ttfts, tpots, tok_counts = [], [], []
    async with httpx.AsyncClient(timeout=180) as client:
        # warmup: unmeasured requests so first-batch effects (graph capture,
        # cache priming, scale-from-zero settling) don't masquerade as the
        # steady-state tail. Count is disclosed in the report.
        for _ in range(args.warmup):
            try:
                await one(client, args.base_url.rstrip("/"), args.model,
                          args.profile, args.api_key, [], [], [])
            except Exception as e:  # noqa: BLE001
                print(f"warn: warmup request failed: {e}")
        t_start = time.perf_counter()
        sem = asyncio.Semaphore(args.concurrency)

        async def guarded():
            async with sem:
                try:
                    await one(client, args.base_url.rstrip("/"), args.model,
                              args.profile, args.api_key, ttfts, tpots, tok_counts)
                except Exception as e:  # noqa: BLE001
                    print(f"warn: request failed: {e}")

        await asyncio.gather(*[guarded() for _ in range(args.requests)])
        wall_s = time.perf_counter() - t_start

    total_tok = sum(n for n, _ in tok_counts)
    agg_tok_s = round(total_tok / wall_s, 1) if wall_s else 0
    usd_mtok = (round(args.pool_usd_hr / (agg_tok_s * 3600) * 1e6, 3)
                if agg_tok_s else None)
    report = {
        "kind": "modular-demo/bench-report", "version": 1,
        "pool": args.pool_name, "pool_usd_hr": args.pool_usd_hr,
        "base_url": args.base_url, "model": args.model,
        "profile": args.profile, "profile_def": PROFILES[args.profile],
        "requests": args.requests, "concurrency": args.concurrency,
        "warmup": args.warmup,
        "completed": len(tok_counts), "wall_s": round(wall_s, 1),
        "output_tok_s_aggregate": agg_tok_s,
        "usd_per_mtok": usd_mtok,
        "p50_ttft_ms": pct(ttfts, 50), "p95_ttft_ms": pct(ttfts, 95),
        "p99_ttft_ms": pct(ttfts, 99),
        "p50_tpot_ms": pct(tpots, 50), "p99_tpot_ms": pct(tpots, 99),
        "slo": {"gate_ttft_ms": args.slo_ttft_ms,
                "pass": (pct(ttfts, 99) or 1e9) <= args.slo_ttft_ms},
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "disclosure": "cost derived from measured tok/s x declared pool price; rerunnable",
    }
    out = Path(args.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in
                      ("pool", "output_tok_s_aggregate", "usd_per_mtok",
                       "p99_ttft_ms", "p99_tpot_ms", "slo")}, indent=2))
    print(f"-> {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--pool-usd-hr", type=float, required=True)
    ap.add_argument("--pool-name", required=True)
    ap.add_argument("--profile", choices=PROFILES, default="docs-agent")
    ap.add_argument("--requests", type=int, default=60)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--warmup", type=int, default=0,
                    help="unmeasured warmup requests before the clock starts")
    ap.add_argument("--slo-ttft-ms", type=float, default=800)
    ap.add_argument("--api-key", default="")
    ap.add_argument("--out", default="bench-reports/report.json")
    asyncio.run(bench(ap.parse_args()))


if __name__ == "__main__":
    main()
