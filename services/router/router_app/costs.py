"""Running cost/usage totals per backend since router start. Feeds GET
/v1/costs and the devboard.

Two record paths share one ledger:
  - record()      legacy predict backends — flat per-request cost + latency
  - record_llm()  LLM backends — cache hit/miss, TTFT, tokens/sec, token cost
The snapshot reports both; LLM-only fields are None for predict backends.
"""

import threading


def _avg(total, n):
    return round(total / n, 2) if n else None


class CostLedger:
    def __init__(self):
        self._lock = threading.Lock()
        self._by_backend: dict[str, dict] = {}

    def _entry(self, model: str, provider: str) -> dict:
        key = f"{model}@{provider}"
        return self._by_backend.setdefault(key, {
            "model": model, "provider": provider, "requests": 0,
            "cache_hits": 0, "served": 0, "est_cost_usd": 0.0,
            "latency_ms_sum": 0.0, "latency_samples": 0, "ttft_ms_sum": 0.0,
            "ttft_samples": 0, "tps_sum": 0.0, "tps_samples": 0,
            "prompt_tokens": 0, "completion_tokens": 0, "slo_met": 0,
        })

    def record(self, model: str, provider: str, est_cost_usd: float,
               latency_ms: float | None = None, cached: bool = False) -> None:
        # Predict path: a router TTL-cache hit served the response WITHOUT a
        # backend call, so `requests` (backend calls) excludes it; `served`
        # (responses) includes it.
        with self._lock:
            entry = self._entry(model, provider)
            entry["served"] += 1
            if cached:
                entry["cache_hits"] += 1
                return
            entry["requests"] += 1
            entry["est_cost_usd"] += est_cost_usd
            if latency_ms is not None:
                entry["latency_ms_sum"] += latency_ms
                entry["latency_samples"] += 1

    def record_llm(self, model: str, provider: str, *, est_cost_usd: float,
                   cache_hit: bool, ttft_ms: float, tokens_per_sec: float,
                   prompt_tokens: int, completion_tokens: int,
                   slo_met: bool = True) -> None:
        # LLM path: a KV/prefix hit is still a backend request (just a cheap
        # one), so it counts toward both `requests` and `served`.
        with self._lock:
            entry = self._entry(model, provider)
            entry["requests"] += 1
            entry["served"] += 1
            if cache_hit:
                entry["cache_hits"] += 1
            if slo_met:
                entry["slo_met"] += 1
            entry["est_cost_usd"] += est_cost_usd
            entry["ttft_ms_sum"] += ttft_ms
            entry["ttft_samples"] += 1
            entry["tps_sum"] += tokens_per_sec
            entry["tps_samples"] += 1
            entry["prompt_tokens"] += prompt_tokens
            entry["completion_tokens"] += completion_tokens

    def snapshot(self) -> dict:
        with self._lock:
            backends = {}
            for key, e in self._by_backend.items():
                total_tokens = e["prompt_tokens"] + e["completion_tokens"]
                usd_per_1m = (round(e["est_cost_usd"] / total_tokens * 1e6, 4)
                              if total_tokens else None)
                backends[key] = {
                    "model": e["model"],
                    "provider": e["provider"],
                    "requests": e["requests"],
                    "cache_hits": e["cache_hits"],
                    "cache_hit_rate": (e["cache_hits"] / e["served"]
                                       if e["served"] else 0.0),
                    "est_cost_usd": round(e["est_cost_usd"], 10),
                    "avg_latency_ms": _avg(e["latency_ms_sum"],
                                           e["latency_samples"]),
                    # LLM-native metrics (None for predict backends)
                    "avg_ttft_ms": _avg(e["ttft_ms_sum"], e["ttft_samples"]),
                    "avg_tokens_per_sec": _avg(e["tps_sum"], e["tps_samples"]),
                    "prompt_tokens": e["prompt_tokens"],
                    "completion_tokens": e["completion_tokens"],
                    "usd_per_1m_tokens": usd_per_1m,
                    "goodput": (round(e["slo_met"] / e["requests"], 4)
                                if e["requests"] else None),
                }
            return {
                "backends": backends,
                "total_requests": sum(b["requests"] for b in backends.values()),
                "total_est_cost_usd": round(
                    sum(b["est_cost_usd"] for b in backends.values()), 10),
            }
