#!/usr/bin/env python3
"""Build the static replay bundle from committed evidence — never fabricate.

Reads benchmarks/raw/ (drill timelines, chaos_drills.csv, devboard snapshots)
and emits site/replay-data.js. Every number in the deployed replay traces to
a file in the repo, per the mission provenance rule.

    python3 tools/replay/build_replay.py
"""
import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RAW = REPO / "benchmarks" / "raw"
OUT = REPO / "site"


def drill_timeline(name: str) -> list[dict]:
    rows = []
    with open(RAW / name) as f:
        for r in csv.DictReader(f):
            rows.append({"t": float(r["t_rel_s"]), "event": r["event"],
                         "detail": r["detail"]})
    return rows


def load_incidents(day: str) -> list[dict]:
    path = RAW / f"devboard-{day}" / "incidents.json"
    incidents = json.loads(path.read_text())
    return [{"id": i["id"], "title": i["title"], "mttr_s": i["mttr_s"],
             "agent": i["agent"], "actions": i["actions"]}
            for i in incidents]


def drills_summary() -> list[dict]:
    out = []
    with open(RAW / "chaos_drills.csv") as f:
        for r in csv.DictReader(f):
            out.append({k: r[k] for k in ("stamp", "scenario", "pool",
                                          "model", "detected_s",
                                          "quarantined_s", "mttr_s",
                                          "resolved")})
    return out


DATA = {
    "generated_from": "benchmarks/raw/ — committed evidence, no synthesis",
    # Scenario 1: deploy with the docs-grounded assistant (2026-07-02/03,
    # deploy/baseten/DEBUG.md + ACTIVATION_RUNBOOK.md + FRICTION_LOG #13-#15)
    "deploy": {
        "attempts": [
            {"name": "L4:2x24x96", "outcome": "never scheduled (30 min silent)",
             "lesson": "2-GPU node scarcity; no capacity signal (friction #6)"},
            {"name": "T4x4x16", "outcome": "host-RAM OOM crash-loop",
             "lesson": "16 GiB host can't materialize 8B weights (friction #7)"},
            {"name": "H100 Engine-Builder", "outcome": "BUILD_FAILED, logs API-invisible",
             "lesson": "docs agent: resources under documented example scale (friction #12)"},
            {"name": "A10Gx8x32", "outcome": "org-gated at push",
             "lesson": "GPU families gated per workspace, no pre-flight (friction #13)"},
            {"name": "T4x8x32 #1", "outcome": "import crash: transformers/vllm skew",
             "lesson": "docs agent + logs: pin transformers==4.53.2 (friction #14)"},
            {"name": "T4x8x32 #2", "outcome": "ACTIVE — but env pointer poisoned",
             "lesson": "promote required after failed first deploy (friction #15)"},
        ],
        "final": {"deployment": "w52yvzr", "instance": "T4x8x32",
                  "model": "Qwen/Qwen3-8B-AWQ (open weights, Apache-2.0)",
                  "engine": "vLLM 0.9.1 custom Truss",
                  "cold_start_s": 360, "warm_ttft_ms": 333,
                  "usd_per_hour": 0.90},
        "agent_findings": [
            {"finding": "Requests during warm-up park then 500 — gate readiness before traffic",
             "source": "docs.baseten.co/deployment/autoscaling/request-lifecycle"},
            {"finding": "Billing starts when a replica is up, not when serving",
             "source": "docs.baseten.co/organization/billing"},
            {"finding": "weights: block (BDN) would cut the 6-min cold start",
             "source": "docs.baseten.co/development/model/bdn"},
            {"finding": "Model API limits are account-tier: 15 RPM unverified / 120 verified",
             "source": "docs.baseten.co/inference/model-apis/rate-limits-and-budgets"},
        ],
    },
    # Scenario 2: real application traffic (2026-07-03 live session)
    "traffic": {
        "requests": [
            {"prompt": "Why do voice agents need low time-to-first-token?",
             "answer": "Voice agents need low time-to-first-token to provide "
                       "immediate feedback and maintain user engagement by "
                       "quickly responding to user input.",
             "replica": "baseten-l4", "model": "Qwen3-8B-AWQ (dedicated T4)",
             "ttft_ms": 332.8, "tokens_per_sec": 25.4,
             "cost_usd": 0.0003583},
            {"prompt": "Name one benefit of KV-cache reuse.",
             "answer": "It significantly reduces latency and computational "
                       "cost by avoiding the re-computation of key and value "
                       "tensors for previously processed tokens.",
             "replica": "model-api-spill",
             "model": "GLM-4.7 (Baseten Model APIs, serverless)",
             "ttft_ms": 717.9, "tokens_per_sec": 210.4,
             "cost_usd": 0.0000638},
        ],
    },
    # Scenario 3: chaos drills (timelines parsed from the committed CSVs)
    "chaos": {
        "baseline": {
            "label": "agent OFF (2026-07-02, live Baseten pool)",
            "timeline": drill_timeline("chaos_drill_latency_20260702-201639.csv"),
            "outcome": "75s of fault — never detected, never resolved",
        },
        "drills": [
            {"label": "latency +600ms on dedicated T4 (2026-07-03)",
             "timeline": drill_timeline("chaos_drill_latency_20260703-154911.csv"),
             "mttr_s": 8.8, "spill_requests": 10,
             "spill_target": "model-api-spill (GLM-4.7 serverless)"},
            {"label": "90% error storm on dedicated T4 (2026-07-03)",
             "timeline": drill_timeline("chaos_drill_errors_20260703-155011.csv"),
             "mttr_s": 9.2, "spill_requests": None,
             "spill_target": "model-api-spill (GLM-4.7 serverless)"},
        ],
        "incidents": load_incidents("20260703"),
        "all_drills": drills_summary(),
    },
    # Scenario 4: cost + latency stats (devboard capture, 2026-07-03 live)
    "stats": {
        "hero": {"blended_cost_per_mtok_usd": 2.17,
                 "cost_vs_single_pool_pct": -27,
                 "mttr_rolling_s": 9,
                 "note": "captured live from /v1/metrics/hero during the "
                         "2026-07-03 session (screenshot + "
                         "benchmarks/raw/devboard-20260703/)"},
        "pools": [
            {"id": "baseten-l4", "model": "Qwen3-8B-AWQ", "kind": "dedicated T4x8x32",
             "ttft_p50_ms": 349.8, "ttft_p99_ms": 484.7, "tpot_p50_ms": 28.6,
             "tpot_p99_ms": 34.0, "slo": "TTFT<500ms TPOT<60ms", "status": "healthy"},
            {"id": "model-api-spill", "model": "GLM-4.7", "kind": "serverless Model API",
             "ttft_p50_ms": 454.3, "ttft_p99_ms": 610.7, "tpot_p50_ms": 8.7,
             "tpot_p99_ms": 80.1, "slo": "TTFT<500ms TPOT<60ms",
             "status": "p99 over voice SLO (fine as spill target)"},
        ],
    },
}

if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    path = OUT / "replay-data.js"
    path.write_text("window.REPLAY = " + json.dumps(DATA, indent=1) + ";\n")
    print(f"wrote {path} "
          f"({len(DATA['chaos']['all_drills'])} drills, "
          f"{len(DATA['chaos']['incidents'])} incidents)")
