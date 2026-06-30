#!/usr/bin/env python3
"""Deterministic autoscaling demo: a warm pool, then idle scale-to-zero, then a
cold-start-aware scale-up under a simulated burst. Every decision streams to an
EventLog (the same shape the devboard reads from /v1/events).

    python3 services/router/scripts/autoscale_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from router_app.autoscaler import AutoScaler, AutoscaleConfig  # noqa: E402
from router_app.events import EventLog  # noqa: E402

# A timeline of (clock_seconds, pending_requests) the controller reacts to.
TIMELINE = [
    (0, 0), (8, 0),         # establish initial replica(s), idle
    (20, 0), (60, 0), (61, 0),   # past idle timeout → scale down
    (61, 12),               # BURST — 12 in-flight
    (69, 12),               # cold starts complete → promote
    (120, 0), (151, 0),     # burst over, idle → scale back down
]


def _run(label: str, min_warm: int) -> int:
    log = EventLog(clock=lambda: 0.0)
    sc = AutoScaler(
        AutoscaleConfig(cold_start_s=8.0, min_warm=min_warm, max_replicas=4,
                        target_pending_per_replica=3, idle_timeout_s=30.0),
        emit=lambda kind, **f: log.emit(kind, **f))

    print(f"\n=== {label} (min_warm={min_warm}) ===")
    print(f"{'t(s)':>5}{'pending':>9}{'warm':>6}{'warming':>9}"
          f"{'draining':>10}  decisions")
    for now, pending in TIMELINE:
        decisions = sc.step(float(now), pending)
        f = sc.fleet
        summary = ", ".join(
            f"{d['action']}"
            + (f"(saved {int(d['cold_start_avoided_ms'])}ms cold start)"
               if d.get("cold_start_avoided_ms") else "")
            for d in decisions) or "—"
        print(f"{now:>5}{pending:>9}{f.count('warm'):>6}"
              f"{f.count('warming'):>9}{f.count('draining'):>10}  {summary}")
    return len(log.recent(kind="scale"))


def main() -> int:
    # Scenario A: no warm pool → genuine scale-to-zero; the burst pays a cold
    # start (the autoscaler is cold-start-AWARE and reports it).
    a = _run("scale-to-zero, cold burst", min_warm=0)
    # Scenario B: a warm pool of 1 → the same burst AVOIDS the cold start.
    b = _run("warm pool absorbs the burst", min_warm=1)
    print(f"\n{a + b} scaling events logged for the devboard.")
    print("A: idle scaled to ZERO replicas, then a cold-start-aware scale-up.")
    print("B: a warm pool let the burst skip the 8000ms cold start.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
