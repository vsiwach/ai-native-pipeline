"""Per-replica KV / prefix-cache state + load — the observed view the affinity
layer and cost model read. Pure data structure; the clock is injected so tests
are deterministic.

Tracks, per replica:
  - which prefix hashes it currently holds (with TTL expiry) → cache-hit lookup
  - in-flight (pending) request count → capacity gating / least-pending
"""

import threading


class KVState:
    def __init__(self, kv_ttl_s: float = 300.0, clock=None):
        self.kv_ttl_s = kv_ttl_s
        self._clock = clock or __import__("time").monotonic
        self._holds: dict[str, dict[str, float]] = {}   # replica -> {prefix: expiry}
        self._pending: dict[str, int] = {}
        self._lock = threading.Lock()

    # --- prefix cache ---------------------------------------------------
    def holds(self, replica: str, prefix: str, now: float | None = None) -> bool:
        now = self._clock() if now is None else now
        with self._lock:
            expiry = self._holds.get(replica, {}).get(prefix)
            if expiry is None:
                return False
            if expiry <= now:
                del self._holds[replica][prefix]
                return False
            return True

    def record_prefix(self, replica: str, prefix: str,
                      now: float | None = None) -> None:
        now = self._clock() if now is None else now
        with self._lock:
            self._holds.setdefault(replica, {})[prefix] = now + self.kv_ttl_s

    def cached_prefixes(self, replica: str, now: float | None = None) -> int:
        now = self._clock() if now is None else now
        with self._lock:
            return sum(1 for e in self._holds.get(replica, {}).values()
                       if e > now)

    # --- load -----------------------------------------------------------
    def pending(self, replica: str) -> int:
        with self._lock:
            return self._pending.get(replica, 0)

    def inc_pending(self, replica: str) -> None:
        with self._lock:
            self._pending[replica] = self._pending.get(replica, 0) + 1

    def dec_pending(self, replica: str) -> None:
        with self._lock:
            self._pending[replica] = max(0, self._pending.get(replica, 0) - 1)
