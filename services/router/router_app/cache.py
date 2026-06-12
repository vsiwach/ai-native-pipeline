"""In-memory TTL response cache. The policy's cache.backend selects the
implementation; only in_memory exists today (redis is a drop-in later — keep
this interface)."""

import hashlib
import json
import threading
import time


def cache_key(model: str, payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"{model}:{hashlib.sha256(canonical.encode()).hexdigest()}"


class TTLCache:
    def __init__(self, ttl_s: float, enabled: bool = True):
        self.ttl_s = ttl_s
        self.enabled = enabled
        self._store: dict[str, tuple[float, bytes]] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> bytes | None:
        if not self.enabled:
            return None
        with self._lock:
            entry = self._store.get(key)
            if entry and entry[0] > time.monotonic():
                self.hits += 1
                return entry[1]
            if entry:
                del self._store[key]
            self.misses += 1
            return None

    def put(self, key: str, value: bytes) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._store[key] = (time.monotonic() + self.ttl_s, value)

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0
