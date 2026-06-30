#!/usr/bin/env python3
"""Repeatable load benchmark: prefix affinity ON vs OFF over a simulated fleet.

Deterministic (seeded). Models the thing that makes affinity matter: each
replica's KV cache is BOUNDED (LRU), as on real hardware. A workload of
requests sharing a small set of prompt prefixes is routed two ways:

  OFF  round-robin (a plain load balancer) — every prefix lands on every
       replica, thrashing each bounded cache → frequent prefill misses.
  ON   the production ConsistentHashRing — each prefix sticks to its owner
       replica, so its working set fits the bounded cache → cache hits.

Reports cache-hit rate and average simulated TTFT for each. Expected: ON wins
on both. Uses the real router affinity primitive (ConsistentHashRing).

    python3 services/router/scripts/affinity_bench.py
"""

import random
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from router_app.affinity import ConsistentHashRing, prefix_hash  # noqa: E402

N_REPLICAS = 4
LRU_CAPACITY = 3          # prefixes a replica's KV can hold at once
N_PREFIXES = 12           # distinct system-prompt / few-shot preambles
COLD_START_MS, PREFILL_MS, CACHE_READ_MS = 8000.0, 400.0, 40.0


class BoundedReplica:
    def __init__(self):
        self.kv: OrderedDict[str, bool] = OrderedDict()
        self.warmed = False

    def serve(self, prefix: str) -> float:
        hit = prefix in self.kv
        if hit:
            self.kv.move_to_end(prefix)
            ttft = CACHE_READ_MS
        else:
            ttft = (0.0 if self.warmed else COLD_START_MS) + PREFILL_MS
            self.kv[prefix] = True
            if len(self.kv) > LRU_CAPACITY:
                self.kv.popitem(last=False)   # evict LRU
        self.warmed = True
        return ttft, hit


def run(enabled: bool, n: int = 600, seed: int = 7) -> dict:
    rng = random.Random(seed)
    fleet = [BoundedReplica() for _ in range(N_REPLICAS)]
    ids = [f"r{i}" for i in range(N_REPLICAS)]
    ring = ConsistentHashRing(ids)
    prefixes = [f"system preamble {i} shared few-shot context" for i in range(N_PREFIXES)]

    hits = 0
    ttft_total = 0.0
    for k in range(n):
        prompt = rng.choice(prefixes)
        ph = prefix_hash(prompt, 16)
        if enabled:
            idx = ids.index(ring.preference(ph)[0])     # owner replica
        else:
            idx = k % N_REPLICAS                         # round-robin spread
        ttft, hit = fleet[idx].serve(ph)
        hits += hit
        ttft_total += ttft
    return {"cache_hit_rate": round(hits / n, 3),
            "avg_ttft_ms": round(ttft_total / n, 1)}


def main() -> int:
    off, on = run(enabled=False), run(enabled=True)
    print(f"{'strategy':<16}{'cache_hit_rate':>16}{'avg_ttft_ms':>14}")
    print(f"{'affinity OFF':<16}{off['cache_hit_rate']:>16}{off['avg_ttft_ms']:>14}")
    print(f"{'affinity ON':<16}{on['cache_hit_rate']:>16}{on['avg_ttft_ms']:>14}")
    better = (on["cache_hit_rate"] > off["cache_hit_rate"]
              and on["avg_ttft_ms"] < off["avg_ttft_ms"])
    print(f"\naffinity improves cache-hit AND ttft: {better}")
    return 0 if better else 1


if __name__ == "__main__":
    sys.exit(main())
