"""The release engine — a traffic-shifting controller. Pure logic, no I/O.

Production inference rollouts must never drop traffic or truncate an in-flight
(often long) generation. This controller shifts traffic between a `stable` and
a `candidate` version under three modes, gated by probes:

  canary  candidate gets an increasing % of real traffic (steps), each step
          gated by a success probe; a failing probe auto-rolls-back.
  shadow  candidate receives a MIRROR of traffic; the client only ever sees
          stable — zero client-visible effect.
  ab      a stable weighted split for comparison (both responses count).

Around a shift it warms up candidate replicas (pre-warm KV) BEFORE sending
them traffic, and drains stable replicas WITHOUT cutting in-flight requests
(stop only once pending hits zero).
"""

import hashlib
from dataclasses import dataclass, field

CANARY, SHADOW, AB = "canary", "shadow", "ab"
IN_PROGRESS, COMPLETE, ROLLED_BACK = "in_progress", "complete", "rolled_back"


def _bucket(key: str) -> int:
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % 100


@dataclass
class Release:
    stable: str
    candidate: str
    mode: str = CANARY
    steps: tuple[int, ...] = (5, 25, 100)
    warmup: bool = True
    drain: bool = True
    step_index: int = -1            # -1 = not started (0% candidate)
    state: str = IN_PROGRESS
    history: list[dict] = field(default_factory=list)

    @property
    def candidate_weight(self) -> int:
        if self.state == ROLLED_BACK or self.step_index < 0:
            return 0
        if self.mode == SHADOW:
            return 0                # shadow never shifts client traffic
        return self.steps[min(self.step_index, len(self.steps) - 1)]

    def route(self, key: str) -> str:
        """Which version serves this request (what the CLIENT sees)."""
        if self.mode == SHADOW:
            return self.stable
        return self.candidate if _bucket(key) < self.candidate_weight \
            else self.stable

    def mirror_to_candidate(self, key: str) -> bool:
        """Shadow mode: mirror every request to candidate (response discarded)."""
        return self.mode == SHADOW and self.state == IN_PROGRESS

    def start(self) -> dict:
        """Begin the rollout: warm up candidate before any traffic shifts."""
        self.step_index = 0
        warmups = [self.candidate] if self.warmup else []
        return self._record("start", warmups=warmups, weight=self.candidate_weight)

    def advance(self, probe_ok: bool) -> dict:
        """Gate the next step on a success probe. A failed probe auto-rolls-back."""
        if self.state != IN_PROGRESS:
            return self._record("noop", weight=self.candidate_weight)
        if not probe_ok:
            return self.rollback(reason="probe_failed")
        if self.step_index >= len(self.steps) - 1:
            self.state = COMPLETE          # already at the final step
            drains = [self.stable] if self.drain else []
            return self._record("complete", drains=drains, weight=100)
        self.step_index += 1
        if self.step_index >= len(self.steps) - 1:
            # advanced INTO the final (100%) step → rollout is complete
            self.state = COMPLETE
            drains = [self.stable] if self.drain else []
            return self._record("complete", drains=drains,
                                weight=self.candidate_weight)
        return self._record("advance", weight=self.candidate_weight)

    def rollback(self, reason: str = "manual") -> dict:
        self.state = ROLLED_BACK
        return self._record("rollback", reason=reason, weight=0)

    def _record(self, action: str, **fields) -> dict:
        event = {"action": action, "mode": self.mode, "stable": self.stable,
                 "candidate": self.candidate, "state": self.state, **fields}
        self.history.append(event)
        return event


def can_stop_drained(pending: int) -> bool:
    """A draining replica may only be stopped once it has no in-flight
    requests — this is what makes a rolling deploy lossless."""
    return pending == 0
