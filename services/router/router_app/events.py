"""A tiny in-memory structured event log. Every router decision — route, scale
(Phase 8), failover/rollout (Phase 9), incident (Phase 10) — emits one event
the devboard renders. Bounded ring buffer; clock injected for deterministic
tests. Not durable by design (swap for a real sink later, like the cache)."""

import threading
from collections import deque


class EventLog:
    def __init__(self, maxlen: int = 2000, clock=None):
        self._events: deque[dict] = deque(maxlen=maxlen)
        self._seq = 0
        self._lock = threading.Lock()
        self._clock = clock or __import__("time").time

    def emit(self, kind: str, **fields) -> dict:
        with self._lock:
            self._seq += 1
            event = {"seq": self._seq, "ts": self._clock(), "kind": kind,
                     **fields}
            self._events.append(event)
            return event

    def seq(self) -> int:
        """Current sequence number (monotonic request-ish counter)."""
        with self._lock:
            return self._seq

    def since(self, seq: int, kind: str | None = None) -> list[dict]:
        """Events after `seq`, oldest first — the streaming-feed tail."""
        with self._lock:
            return [e for e in self._events if e["seq"] > seq
                    and (kind is None or e["kind"] == kind)]

    def recent(self, limit: int = 100, kind: str | None = None) -> list[dict]:
        with self._lock:
            items = [e for e in self._events if kind is None or e["kind"] == kind]
        return items[-limit:]

    def kinds(self) -> dict:
        with self._lock:
            counts: dict[str, int] = {}
            for e in self._events:
                counts[e["kind"]] = counts.get(e["kind"], 0) + 1
            return counts
