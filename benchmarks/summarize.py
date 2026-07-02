#!/usr/bin/env python3
"""Summarize raw benchmark CSVs: per-pool TTFT/TPOT percentiles, goodput at
the voice SLO, $/1M output tokens — and, for sweep runs, the goodput curve
artifact the devboard renders (benchmarks/goodput.json).

The devboard/docs never show a number this module can't recompute from the
raw rows — run it yourself; that's the SLO-AUDITOR contract.

Usage:
  python3 benchmarks/summarize.py benchmarks/raw/steady-c8-*.csv
  python3 benchmarks/summarize.py --goodput-out benchmarks/goodput.json \
      benchmarks/raw/sweep-c*-20260701-*.csv
"""

import argparse
import csv
import glob
import json
from collections import defaultdict

SLO_TTFT_MS = 500.0   # voice tier (mission): TTFT p99 < 500ms
SLO_TPOT_MS = 60.0    # voice tier (mission): TPOT p99 < 60ms


def percentile(sorted_vals, q):
    if not sorted_vals:
        return 0.0
    idx = max(0, min(len(sorted_vals) - 1,
                     round(q / 100.0 * len(sorted_vals)) - 1))
    return sorted_vals[idx]


def load_rows(patterns):
    rows = []
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            with open(path) as f:
                rows.extend(csv.DictReader(f))
    return rows


def _f(row, key):
    try:
        return float(row[key])
    except (KeyError, TypeError, ValueError):
        return None


def slo_met(row):
    ttft = _f(row, "client_ttft_ms")
    tpot = _f(row, "tpot_ms")
    return (row.get("http_status") == "200" and ttft is not None
            and ttft <= SLO_TTFT_MS
            and (tpot is None or tpot <= SLO_TPOT_MS))


def pool_summary(rows):
    """Per-pool percentile table + $/1M output tokens + goodput rate."""
    by_pool = defaultdict(list)
    for r in rows:
        by_pool[r.get("replica") or "unrouted"].append(r)
    out = {}
    for pool, rs in sorted(by_pool.items()):
        ok = [r for r in rs if r.get("http_status") == "200"]
        ttft = sorted(v for v in (_f(r, "client_ttft_ms") for r in ok)
                      if v is not None)
        tpot = sorted(v for v in (_f(r, "tpot_ms") for r in ok)
                      if v is not None)
        tokens = sum(int(r["completion_tokens"] or 0) for r in ok)
        cost = sum(float(r["est_cost_usd"] or 0) for r in ok)
        seconds = _span_seconds(rs)
        good = sum(1 for r in rs if slo_met(r))
        out[pool] = {
            "requests": len(rs), "errors": len(rs) - len(ok),
            "ttft_ms": {"p50": round(percentile(ttft, 50), 1),
                        "p95": round(percentile(ttft, 95), 1),
                        "p99": round(percentile(ttft, 99), 1)},
            "tpot_ms": {"p50": round(percentile(tpot, 50), 2),
                        "p95": round(percentile(tpot, 95), 2),
                        "p99": round(percentile(tpot, 99), 2)},
            "slo_ttft_p99_met": percentile(ttft, 99) <= SLO_TTFT_MS,
            "slo_tpot_p99_met": percentile(tpot, 99) <= SLO_TPOT_MS,
            "goodput_rps": round(good / seconds, 2) if seconds else 0.0,
            "usd_per_1m_output_tokens":
                round(cost / tokens * 1_000_000, 4) if tokens else 0.0,
        }
    return out


def _span_seconds(rows):
    ts = sorted(float(r["ts"]) for r in rows if r.get("ts"))
    return (ts[-1] - ts[0]) if len(ts) > 1 else 0.0


def goodput_curve(rows):
    """conc -> SLO-passing req/s, per pool and blended (sweep runs)."""
    by_conc = defaultdict(list)
    for r in rows:
        by_conc[int(r.get("concurrency") or 0)].append(r)
    curves = defaultdict(list)
    for conc in sorted(by_conc):
        rs = by_conc[conc]
        seconds = _span_seconds(rs)
        if not seconds:
            continue
        good = sum(1 for r in rs if slo_met(r))
        curves["blended"].append({"conc": conc,
                                  "tps": round(good / seconds, 2)})
        by_pool = defaultdict(list)
        for r in rs:
            if r.get("replica"):
                by_pool[r["replica"]].append(r)
        for pool, prs in by_pool.items():
            pgood = sum(1 for r in prs if slo_met(r))
            curves[pool].append({"conc": conc,
                                 "tps": round(pgood / seconds, 2)})
    out = {}
    for pool, points in curves.items():
        best = max(points, key=lambda p: p["tps"], default=None)
        slo_max = 0
        for pt in points:   # highest conc where goodput still ~peak (>=95%)
            if best and pt["tps"] >= 0.95 * best["tps"]:
                slo_max = max(slo_max, pt["conc"])
        out[pool] = {"points": points, "slo_max_conc": slo_max}
    return out


def render(summary):
    lines = [f"{'pool':<14}{'req':>6}{'err':>5}"
             f"{'TTFT p50/p95/p99':>22}{'TPOT p50/p95/p99':>22}"
             f"{'goodput':>9}{'$/1M tok':>10}"]
    for pool, s in summary.items():
        t, d = s["ttft_ms"], s["tpot_ms"]
        lines.append(
            f"{pool:<14}{s['requests']:>6}{s['errors']:>5}"
            f"{t['p50']:>8}/{t['p95']}/{t['p99']}"
            f"{d['p50']:>10}/{d['p95']}/{d['p99']}"
            f"{s['goodput_rps']:>9}{s['usd_per_1m_output_tokens']:>10}")
    lines.append(f"voice SLO: TTFT p99<{SLO_TTFT_MS:.0f}ms, "
                 f"TPOT p99<{SLO_TPOT_MS:.0f}ms")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("patterns", nargs="+", help="raw CSV globs")
    p.add_argument("--json", action="store_true", help="print JSON")
    p.add_argument("--goodput-out",
                   help="write goodput curve artifact (sweep runs)")
    args = p.parse_args(argv)

    rows = load_rows(args.patterns)
    if not rows:
        raise SystemExit("no rows matched")
    summary = pool_summary(rows)
    print(json.dumps(summary, indent=2) if args.json else render(summary))
    if args.goodput_out:
        curves = goodput_curve(rows)
        with open(args.goodput_out, "w") as f:
            json.dump(curves, f, indent=2)
        print(f"goodput curves -> {args.goodput_out}")


if __name__ == "__main__":
    main()
