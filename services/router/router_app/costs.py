"""Running cost/usage totals per backend endpoint since router start.
Feeds GET /v1/costs and the Phase 5 dashboard."""

import threading


class CostLedger:
    def __init__(self):
        self._lock = threading.Lock()
        self._by_backend: dict[str, dict] = {}

    def record(self, model: str, provider: str, est_cost_usd: float,
               latency_ms: float | None = None, cached: bool = False) -> None:
        key = f"{model}@{provider}"
        with self._lock:
            entry = self._by_backend.setdefault(key, {
                "model": model, "provider": provider, "requests": 0,
                "cache_hits": 0, "est_cost_usd": 0.0, "latency_ms_sum": 0.0,
                "latency_samples": 0,
            })
            if cached:
                entry["cache_hits"] += 1
                return
            entry["requests"] += 1
            entry["est_cost_usd"] += est_cost_usd
            if latency_ms is not None:
                entry["latency_ms_sum"] += latency_ms
                entry["latency_samples"] += 1

    def snapshot(self) -> dict:
        with self._lock:
            backends = {}
            for key, e in self._by_backend.items():
                served = e["requests"] + e["cache_hits"]
                backends[key] = {
                    "model": e["model"],
                    "provider": e["provider"],
                    "requests": e["requests"],
                    "cache_hits": e["cache_hits"],
                    "cache_hit_rate": (e["cache_hits"] / served) if served else 0.0,
                    "est_cost_usd": round(e["est_cost_usd"], 10),
                    "avg_latency_ms": (
                        round(e["latency_ms_sum"] / e["latency_samples"], 2)
                        if e["latency_samples"] else None
                    ),
                }
            return {
                "backends": backends,
                "total_requests": sum(b["requests"] for b in backends.values()),
                "total_est_cost_usd": round(
                    sum(b["est_cost_usd"] for b in backends.values()), 10),
            }
