#!/usr/bin/env python3
"""Deterministic release-engine demo: a healthy canary that reaches 100%, a
canary that auto-rolls-back on an SLO breach, and a shadow deploy that mirrors
traffic with no client-visible effect. Decisions stream to an EventLog (the
shape the devboard reads from /v1/events).

    python3 services/router/scripts/release_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from router_app.events import EventLog  # noqa: E402
from router_app.release import CANARY, SHADOW, Release  # noqa: E402


def _split(rel, n=1000):
    to_candidate = sum(1 for i in range(n) if rel.route(f"req-{i}") == rel.candidate)
    return round(100 * to_candidate / n)


def main() -> int:
    log = EventLog(clock=lambda: 0.0)

    print("=== canary: healthy rollout 5% → 25% → 100% (probe passes) ===")
    rel = Release("v1", "v2", mode=CANARY, steps=(5, 25, 100))

    def step(ev):
        # print observed split BEFORE the next transition mutates the release
        log.emit("rollout", **ev)
        print(f"  {ev['action']:<9} weight={ev['weight']:>3}%  "
              f"observed≈{_split(rel)}%  state={ev['state']}")

    step(rel.start())
    step(rel.advance(True))
    step(rel.advance(True))

    print("\n=== canary: probe breach at 25% → auto-rollback ===")
    rel = Release("v1", "v3", mode=CANARY, steps=(5, 25, 100))
    log.emit("rollout", **rel.start())
    log.emit("rollout", **rel.advance(True))                 # → 25%
    ev = rel.advance(probe_ok=False)                         # SLO breach
    log.emit("rollout", **ev)
    print(f"  rolled_back: reason={ev['reason']}  candidate now gets "
          f"{_split(rel)}% (all traffic back on stable)")

    print("\n=== shadow: mirror traffic to candidate, client sees stable only ===")
    rel = Release("v1", "v4", mode=SHADOW, steps=(0,))
    log.emit("rollout", **rel.start())
    client_versions = {rel.route(f"r{i}") for i in range(100)}
    mirrored = all(rel.mirror_to_candidate(f"r{i}") for i in range(100))
    print(f"  client sees: {client_versions}  | mirrored to candidate: {mirrored}")

    print(f"\n{len(log.recent(kind='rollout'))} rollout events logged for the "
          f"devboard. Zero-drop drains are gated by release.can_stop_drained().")
    return 0


if __name__ == "__main__":
    sys.exit(main())
