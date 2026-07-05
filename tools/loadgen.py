#!/usr/bin/env python3
"""Synthetic load generator — drives a route like real traffic, no human
(and no smart model) required.

Where tools/replay.py sends the eval set once, sequentially, this generates
an open-loop workload: seeded Poisson arrivals at a target RPS, a mix of
request profiles (prefill-heavy vs latency-critical), a stream/non-stream
ratio, and a concurrency cap. The router does the rest (shadow mirroring,
metrics, costs) — the console's panels move exactly as they would under
production traffic, sim or real upstream alike.

Deterministic planning: the schedule is generated up front from --seed, so
a run is reproducible and the plan logic is unit-testable without sockets.
Client-measured TTFT/total per request; optional CSV for evidence.

Usage:
  python3 tools/loadgen.py --router http://localhost:8114 --route docs-assist \
      --rps 2 --duration 60 --concurrency 8 --stream-ratio 0.5 \
      --mix docs-agent=0.7,voice=0.3 --seed 42 \
      --out benchmarks/raw/loadgen_docs-assist.csv
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path

# Mirrors tools/bench.py's workload profiles (PRD F0.2): prompt padding
# approximates prefill weight, max_tokens bounds decode length.
PROFILES = {
    "docs-agent": {"prompt_pad": 1800, "max_tokens": 300},
    "coding-agent": {"prompt_pad": 3500, "max_tokens": 900},
    "voice": {"prompt_pad": 300, "max_tokens": 80},
}


@dataclass(frozen=True)
class PlannedRequest:
    t_offset_s: float
    question: str
    profile: str
    stream: bool
    max_tokens: int


def parse_mix(spec: str) -> list[tuple[str, float]]:
    """'docs-agent=0.7,voice=0.3' -> [('docs-agent', .7), ('voice', .3)],
    weights normalized; unknown profiles are an error."""
    pairs = []
    for part in spec.split(","):
        name, _, w = part.strip().partition("=")
        if name not in PROFILES:
            raise ValueError(f"unknown profile {name!r} "
                             f"(choose from {sorted(PROFILES)})")
        weight = float(w) if w else 1.0
        if weight <= 0:
            raise ValueError(f"weight for {name!r} must be > 0")
        pairs.append((name, weight))
    total = sum(w for _, w in pairs)
    return [(n, w / total) for n, w in pairs]


def plan(seed: int, duration_s: float, rps: float, stream_ratio: float,
         mix: list[tuple[str, float]], questions: list[str]) -> list[PlannedRequest]:
    """The full request schedule, generated up front: Poisson arrivals at
    `rps` until `duration_s`, profile drawn from `mix`, stream flag drawn
    at `stream_ratio`. Same seed -> same plan, always."""
    if not questions:
        raise ValueError("no questions to send")
    rng = random.Random(seed)
    names = [n for n, _ in mix]
    weights = [w for _, w in mix]
    out, t = [], 0.0
    while True:
        t += rng.expovariate(rps)
        if t >= duration_s:
            return out
        profile = rng.choices(names, weights=weights)[0]
        out.append(PlannedRequest(
            t_offset_s=round(t, 4),
            question=rng.choice(questions),
            profile=profile,
            stream=rng.random() < stream_ratio,
            max_tokens=PROFILES[profile]["max_tokens"],
        ))


def pct(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    return round(xs[min(len(xs) - 1, int(len(xs) * p / 100))], 1)


def summarize(rows: list[dict]) -> dict:
    ok = [r for r in rows if r["status"] == 200]
    ttfts = [r["ttft_ms"] for r in ok if r["ttft_ms"] is not None]
    return {
        "sent": len(rows),
        "ok": len(ok),
        "errors": len(rows) - len(ok),
        "p50_ttft_ms": pct(ttfts, 50),
        "p95_ttft_ms": pct(ttfts, 95),
        "p99_ttft_ms": pct(ttfts, 99),
        "p99_total_ms": pct([r["total_ms"] for r in ok], 99),
        "streamed": sum(1 for r in ok if r["stream"]),
    }


async def _fire(client, args, req: PlannedRequest, rows: list[dict],
                sem: asyncio.Semaphore) -> None:
    pad = "modular " * (PROFILES[req.profile]["prompt_pad"] // 2)
    body = {
        "messages": [{"role": "system", "content": pad},
                     {"role": "user", "content": req.question}],
        "max_tokens": req.max_tokens,
        "stream": req.stream,
        "temperature": 0,   # reproducible answers for certification cohorts
    }
    url = f"{args.router}/v1/chat/completions"
    row = {"t_offset_s": req.t_offset_s, "profile": req.profile,
           "stream": req.stream, "status": 0, "replica": None,
           "ttft_ms": None, "total_ms": None}
    async with sem:
        t0 = time.perf_counter()
        try:
            if req.stream:
                async with client.stream(
                        "POST", url, params={"model": args.route},
                        json=body) as r:
                    row["status"] = r.status_code
                    row["replica"] = r.headers.get("X-Replica")
                    async for line in r.aiter_lines():
                        if line.startswith("data:") and "[DONE]" not in line:
                            if row["ttft_ms"] is None:
                                row["ttft_ms"] = round(
                                    (time.perf_counter() - t0) * 1000, 1)
            else:
                r = await client.post(url, params={"model": args.route},
                                      json=body)
                row["status"] = r.status_code
                row["replica"] = r.headers.get("X-Replica")
                row["ttft_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        except Exception as exc:  # noqa: BLE001 — an error is a data point
            row["error"] = str(exc)[:120]
        row["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    rows.append(row)


async def run(args) -> dict:
    import httpx  # lazy: planning/summary stay importable stdlib-only

    questions = [json.loads(l)["question"]
                 for l in Path(args.evals).read_text().splitlines()
                 if l.strip()]
    schedule = plan(args.seed, args.duration, args.rps, args.stream_ratio,
                    parse_mix(args.mix), questions)
    print(f"plan: {len(schedule)} requests over {args.duration}s "
          f"(~{args.rps} rps, seed {args.seed})")
    rows: list[dict] = []
    sem = asyncio.Semaphore(args.concurrency)
    async with httpx.AsyncClient(timeout=120) as client:
        t0 = time.perf_counter()
        tasks = []
        last_report = 0.0
        for req in schedule:
            delay = req.t_offset_s - (time.perf_counter() - t0)
            if delay > 0:
                await asyncio.sleep(delay)
            tasks.append(asyncio.create_task(
                _fire(client, args, req, rows, sem)))
            now = time.perf_counter() - t0
            if now - last_report >= 5:
                last_report = now
                s = summarize(rows)
                print(f"  t+{now:4.0f}s sent={len(tasks)} done={s['sent']} "
                      f"err={s['errors']} p50_ttft={s['p50_ttft_ms']}ms")
        await asyncio.gather(*tasks)
    summary = summarize(rows)
    print(json.dumps(summary, indent=2))
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        fields = ["t_offset_s", "profile", "stream", "status", "replica",
                  "ttft_ms", "total_ms", "error"]
        with out.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(sorted(rows, key=lambda r: r["t_offset_s"]))
        print(f"-> {out}")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--router", default="http://localhost:8114")
    ap.add_argument("--route", default="docs-assist")
    ap.add_argument("--evals", default="evals/docs_qa.jsonl",
                    help="question pool (only the question text is used)")
    ap.add_argument("--rps", type=float, default=1.0)
    ap.add_argument("--duration", type=float, default=60.0)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--stream-ratio", type=float, default=0.5)
    ap.add_argument("--mix", default="docs-agent=0.7,voice=0.3")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=None, help="per-request CSV path")
    args = ap.parse_args()
    summary = asyncio.run(run(args))
    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
