"""MetricsWindow — per-request latency/economics samples for the devboard.

Every request the router proxies lands here as one sample; every number the
devboard shows derives from these samples (or from benchmarks/raw CSVs the
harness writes from the same fields) — the SLO-AUDITOR provenance chain.

Pure computation + injected clock; thread-safe ring buffer. No I/O.
"""

import threading
from bisect import insort
from dataclasses import dataclass


@dataclass
class Sample:
    ts: float
    model: str
    replica: str        # replica/pool id, e.g. baseten-l4
    provider: str
    ttft_ms: float
    tpot_ms: float      # decode_ms / completion_tokens
    prompt_tokens: int
    completion_tokens: int
    est_cost_usd: float
    ttft_slo_met: bool
    tpot_slo_met: bool

    @property
    def slo_met(self) -> bool:
        return self.ttft_slo_met and self.tpot_slo_met


def percentile(sorted_vals: list[float], q: float) -> float:
    """Nearest-rank percentile on a pre-sorted list; 0.0 when empty."""
    if not sorted_vals:
        return 0.0
    idx = max(0, min(len(sorted_vals) - 1,
                     round(q / 100.0 * len(sorted_vals)) - 1))
    return sorted_vals[idx]


def histogram(vals: list[float], buckets: int = 24) -> dict:
    """{edges, counts} over vals — feeds the devboard density strips."""
    if not vals:
        return {"edges": [], "counts": []}
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        hi = lo + 1.0
    width = (hi - lo) / buckets
    counts = [0] * buckets
    for v in vals:
        counts[min(buckets - 1, int((v - lo) / width))] += 1
    edges = [round(lo + i * width, 3) for i in range(buckets + 1)]
    return {"edges": edges, "counts": counts}


class MetricsWindow:
    def __init__(self, max_samples: int = 50_000, clock=None):
        import time
        self._clock = clock or time.time
        self._max = max_samples
        self._samples: list[Sample] = []
        self._lock = threading.Lock()

    def record(self, **fields) -> None:
        with self._lock:
            self._samples.append(Sample(ts=self._clock(), **fields))
            if len(self._samples) > self._max:
                del self._samples[: len(self._samples) - self._max]

    def window(self, seconds: float, now: float | None = None) -> list[Sample]:
        now = self._clock() if now is None else now
        cutoff = now - seconds
        with self._lock:
            return [s for s in self._samples if s.ts >= cutoff]

    # ---- aggregations (all pure over window snapshots) ---------------------

    @staticmethod
    def by_replica(samples: list[Sample]) -> dict[str, list[Sample]]:
        out: dict[str, list[Sample]] = {}
        for s in samples:
            out.setdefault(s.replica, []).append(s)
        return out

    @staticmethod
    def latency_stats(samples: list[Sample], field: str) -> dict:
        vals: list[float] = []
        for s in samples:
            insort(vals, getattr(s, field))
        return {"p50": round(percentile(vals, 50), 1),
                "p95": round(percentile(vals, 95), 1),
                "p99": round(percentile(vals, 99), 1),
                "hist": histogram(vals)}

    @staticmethod
    def cost_per_mtok(samples: list[Sample]) -> float:
        tokens = sum(s.completion_tokens for s in samples)
        cost = sum(s.est_cost_usd for s in samples)
        return round(cost / tokens * 1_000_000, 4) if tokens else 0.0

    @staticmethod
    def slo_rate(samples: list[Sample]) -> float:
        if not samples:
            return 1.0
        return sum(1 for s in samples if s.slo_met) / len(samples)

    def hourly_series(self, hours: int, field: str,
                      now: float | None = None) -> list[float]:
        """Mean of `field` per hour bucket, oldest first; 0.0 = no data
        (rendered as a gap, never a fabricated value)."""
        now = self._clock() if now is None else now
        samples = self.window(hours * 3600.0, now)
        buckets: list[list[float]] = [[] for _ in range(hours)]
        for s in samples:
            idx = min(hours - 1, int((now - s.ts) // 3600.0))
            buckets[idx].append(getattr(s, field))
        series = [round(sum(b) / len(b), 4) if b else 0.0 for b in buckets]
        return list(reversed(series))

    def hourly_cost_series(self, hours: int,
                           now: float | None = None) -> list[float]:
        now = self._clock() if now is None else now
        samples = self.window(hours * 3600.0, now)
        buckets: list[list[Sample]] = [[] for _ in range(hours)]
        for s in samples:
            idx = min(hours - 1, int((now - s.ts) // 3600.0))
            buckets[idx].append(s)
        return list(reversed([self.cost_per_mtok(b) if b else 0.0
                              for b in buckets]))
