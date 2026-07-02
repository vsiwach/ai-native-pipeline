"""Devboard data surface — builders (pure) + route shapes vs the contract.

Every builder is driven with synthetic samples and an injected clock; the
HTTP tests only assert contract shape (keys/types), since values are checked
at the builder level.
"""

import unittest

from router_app import devboard
from router_app.incidents import IncidentStore
from router_app.metrics import MetricsWindow, histogram, percentile


class FakeClock:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


def fill(metrics, clock, replica, n, ttft=100.0, tpot=25.0, tokens=100,
         cost=0.0001, slo=True):
    for _ in range(n):
        metrics.record(model="qwen3-8b", replica=replica, provider=replica,
                       ttft_ms=ttft, tpot_ms=tpot, prompt_tokens=50,
                       completion_tokens=tokens, est_cost_usd=cost,
                       ttft_slo_met=slo, tpot_slo_met=slo)
        clock.advance(0.01)


class MetricsMathTest(unittest.TestCase):
    def test_percentile_nearest_rank(self):
        vals = sorted(float(v) for v in range(1, 101))
        self.assertEqual(percentile(vals, 50), 50.0)
        self.assertEqual(percentile(vals, 99), 99.0)
        self.assertEqual(percentile([], 99), 0.0)

    def test_histogram_covers_range(self):
        h = histogram([1.0, 2.0, 3.0, 100.0], buckets=4)
        self.assertEqual(sum(h["counts"]), 4)
        self.assertEqual(len(h["edges"]), 5)
        self.assertEqual(histogram([]), {"edges": [], "counts": []})

    def test_cost_per_mtok(self):
        clock = FakeClock()
        m = MetricsWindow(clock=clock)
        fill(m, clock, "vllm-l4", 10, tokens=1000, cost=0.001)
        # 0.01 USD for 10k tokens -> $1.00 per 1M
        samples = m.window(60)
        self.assertAlmostEqual(MetricsWindow.cost_per_mtok(samples), 1.0)

    def test_hourly_series_gaps_are_zero_not_fabricated(self):
        clock = FakeClock()
        m = MetricsWindow(clock=clock)
        fill(m, clock, "vllm-l4", 5, tpot=30.0)
        series = m.hourly_series(24, "tpot_ms")
        self.assertEqual(len(series), 24)
        self.assertEqual(series[:-1], [0.0] * 23)   # no data -> 0, not filler
        self.assertAlmostEqual(series[-1], 30.0)


class HeroTest(unittest.TestCase):
    def test_hero_blends_and_deltas(self):
        clock = FakeClock()
        m = MetricsWindow(clock=clock)
        inc = IncidentStore(clock=clock)
        fill(m, clock, "baseten-l4", 20, tpot=40.0, tokens=100, cost=0.0002)
        fill(m, clock, "vllm-l4", 20, tpot=30.0, tokens=100, cost=0.0001)
        out = devboard.hero(m, inc, tpot_slo_ms=60, now=clock())
        self.assertEqual(out["tpot_slo_ms"], 60)
        self.assertGreater(out["tpot_p99_ms"], 0)
        # blended 40 tok-$2/M and 30 tok-$1/M -> blended < single (priciest)
        self.assertLess(out["cost_per_mtok_usd"], 2.0)
        self.assertLess(out["cost_delta_pct"], 0)   # cheaper than single-pool
        self.assertEqual(len(out["spark"]["tpot"]), 24)

    def test_hero_empty_state_is_zeros(self):
        clock = FakeClock()
        out = devboard.hero(MetricsWindow(clock=clock),
                            IncidentStore(clock=clock), tpot_slo_ms=60,
                            now=clock())
        self.assertEqual(out["tpot_p99_ms"], 0.0)
        self.assertEqual(out["cost_per_mtok_usd"], 0.0)
        self.assertEqual(out["mttr_s"], 0.0)


REPLICAS = [
    {"id": "baseten-l4", "provider": "baseten-l4", "url": "http://b:8080"},
    {"id": "vllm-l4", "provider": "runpod-vllm-l4", "url": "http://v:8080"},
]


class SloPanelTest(unittest.TestCase):
    def test_per_pool_percentiles_and_slo(self):
        clock = FakeClock()
        m = MetricsWindow(clock=clock)
        fill(m, clock, "baseten-l4", 50, ttft=200.0, tpot=40.0)
        fill(m, clock, "vllm-l4", 50, ttft=150.0, tpot=30.0)
        out = devboard.slo_panel(
            m, REPLICAS, {"ttft_ms": 500, "tpot_ms": 60},
            is_usable=lambda u: True, pending_of=lambda r: 2, now=clock())
        pools = {p["id"]: p for p in out["pools"]}
        self.assertEqual(pools["baseten-l4"]["ttft"]["p99"], 200.0)
        self.assertEqual(pools["baseten-l4"]["ttft"]["slo"], 500)
        self.assertEqual(pools["vllm-l4"]["tpot"]["p50"], 30.0)
        self.assertIn("hist", pools["vllm-l4"]["tpot"])
        # no bench artifact -> no fabricated curve, live operating point only
        self.assertEqual(pools["vllm-l4"]["goodput"]["points"], [])
        self.assertEqual(pools["vllm-l4"]["goodput"]["operating"]["conc"], 2)

    def test_ejected_pool_health_zero(self):
        clock = FakeClock()
        m = MetricsWindow(clock=clock)
        out = devboard.slo_panel(
            m, REPLICAS, {}, is_usable=lambda u: "v:" not in u,
            pending_of=lambda r: 0, now=clock())
        pools = {p["id"]: p for p in out["pools"]}
        self.assertEqual(pools["vllm-l4"]["health"], 0.0)
        self.assertEqual(pools["vllm-l4"]["status"], "bad")


class PoolsSnapshotTest(unittest.TestCase):
    def test_pools_shape_and_ejection(self):
        clock = FakeClock()
        m = MetricsWindow(clock=clock)
        fill(m, clock, "baseten-l4", 10, tokens=1000, cost=0.001)
        entry = {"max_replicas": 4, "scale_to_zero": True}
        out = devboard.pools_snapshot(
            m, REPLICAS, entry, is_usable=lambda u: "v:" not in u,
            pending_of=lambda r: 4, capacity=8, now=clock())
        pools = {p["id"]: p for p in out["pools"]}
        b = pools["baseten-l4"]
        self.assertEqual(b["util_pct"], 50.0)
        self.assertEqual(b["autoscaler"]["max"], 4)
        self.assertEqual(b["autoscaler"]["min"], 0)
        self.assertEqual(b["cost_per_mtok"], 1.0)
        v = pools["vllm-l4"]
        self.assertEqual(v["autoscaler"]["replicas"], 0)
        self.assertEqual(v["autoscaler"]["state"], "ejected")
        self.assertEqual(v["status"], "bad")


class IncidentStoreTest(unittest.TestCase):
    def test_lifecycle_phases_and_mttr(self):
        clock = FakeClock()
        store = IncidentStore(clock=clock)
        inc = store.open("vllm-l4 replica stuck after OOM", agent=True)
        clock.advance(6)
        store.act(inc["id"], "correlated OOM kills", phase="diagnose")
        clock.advance(8)
        store.act(inc["id"], "ejected replica; spilled traffic",
                  phase="resolve")
        clock.advance(33)
        done = store.resolve(inc["id"], postmortem_url="/pm/PM-1")
        self.assertEqual(done["mttr_s"], 47.0)
        self.assertEqual(done["phase_ms"]["detect"], 6000.0)
        self.assertEqual(done["phase_ms"]["diagnose"], 8000.0)
        self.assertEqual(done["phase_ms"]["resolve"], 33000.0)
        self.assertFalse(done["live"])

    def test_live_incident_counts_up_and_medians(self):
        clock = FakeClock()
        store = IncidentStore(clock=clock)
        for mttr, agent in ((150, False), (146, False), (45, True), (49, True)):
            inc = store.open("drill", agent=agent)
            clock.advance(mttr)
            store.resolve(inc["id"])
        self.assertEqual(store.mttr_median(agent=True), 47.0)
        self.assertEqual(store.mttr_median(agent=False), 148.0)
        live = store.open("live one", agent=True)
        clock.advance(12)
        snap = store.snapshot()
        self.assertEqual(snap[0]["id"], live["id"])   # newest first
        self.assertEqual(snap[0]["mttr_s"], 12.0)     # counting up
        self.assertNotIn("_phase", snap[0])


class FeedAndReleaseTest(unittest.TestCase):
    def test_feed_item_maps_route_events_only(self):
        ev = {"kind": "route", "req": "#0042", "wl_tier": "realtime",
              "tag": "hipaa", "replica": "baseten-l4",
              "reason": "right-of-way", "decide_ms": 3.2,
              "iso_ts": "2026-07-01T12:00:00Z"}
        item = devboard.feed_item(ev)
        self.assertEqual(item["pool"], "baseten-l4")
        self.assertEqual(item["tier"], "realtime")
        self.assertIsNone(devboard.feed_item({"kind": "scale"}))

    def test_release_steady_and_canary(self):
        from router_app.release import Release
        steady = devboard.release_active(None, "qwen3-8b")
        self.assertEqual(steady["strategy"], "steady")
        self.assertEqual(steady["steps"][0]["status"], "pass")
        rel = Release(stable="v13", candidate="v14", steps=(1, 10, 50, 100))
        rel.start()
        rel.advance(probe_ok=True)
        out = devboard.release_active(rel, "qwen3-8b")
        self.assertEqual(out["to"], "v14")
        self.assertEqual([s["status"] for s in out["steps"]],
                         ["pass", "live", "wait", "wait"])
        rel.rollback("probe_failed")
        out = devboard.release_active(rel, "qwen3-8b")
        self.assertEqual(out["steps"][1]["status"], "fail")


if __name__ == "__main__":
    unittest.main()
