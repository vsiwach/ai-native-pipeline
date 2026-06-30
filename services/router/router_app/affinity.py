"""Prefix/KV affinity — pure logic, no I/O.

LLM serving is stateful: a request that shares a prompt prefix with an earlier
one is far cheaper on the replica that still holds that prefix's KV (a cache
hit skips prefill). So we route by prefix.

Strategy `consistent_hash`: the prefix hash maps onto a hash ring of replicas;
the ring gives a STABLE preference order, so the same prefix keeps landing on
the same replica, and when that replica is unhealthy or full, traffic re-lands
consistently on the next replica (not reshuffled globally) as replicas come and
go. This is the mechanism behind every acceptance test in this phase.
"""

import bisect
import hashlib


def prefix_hash(prompt: str, prefix_tokens: int) -> str:
    """Hash the first `prefix_tokens` of the prompt (1 token ≈ 4 chars). Two
    prompts sharing that prefix collide — the whole point. Matches the llm
    simulator's KV key algorithm so router and backend agree on 'same prefix'."""
    prefix_chars = max(1, prefix_tokens) * 4
    return hashlib.sha256(prompt[:prefix_chars].encode()).hexdigest()[:16]


def _hash_point(key: str) -> int:
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16)


class ConsistentHashRing:
    """Maps keys to replicas with minimal disruption when the replica set
    changes. `vnodes` virtual nodes per replica smooth the distribution."""

    def __init__(self, replicas: list[str], vnodes: int = 64):
        self.vnodes = vnodes
        self._ring: list[tuple[int, str]] = []
        for r in replicas:
            for v in range(vnodes):
                self._ring.append((_hash_point(f"{r}#{v}"), r))
        self._ring.sort()
        self._points = [p for p, _ in self._ring]

    def preference(self, key: str) -> list[str]:
        """Replicas in consistent-hash preference order for `key` — the owner
        first, then the next distinct replicas clockwise. Deterministic."""
        if not self._ring:
            return []
        start = bisect.bisect(self._points, _hash_point(key))
        seen: list[str] = []
        n = len(self._ring)
        for i in range(n):
            _, replica = self._ring[(start + i) % n]
            if replica not in seen:
                seen.append(replica)
        return seen
