"""summarize.py — pure aggregation math over synthetic raw rows."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import summarize  # noqa: E402


def row(ts, replica="vllm-l4", ttft=100.0, tpot=25.0, tokens=50,
        cost=0.00005, status="200", conc=4):
    return {"ts": str(ts), "replica": replica, "http_status": status,
            "client_ttft_ms": str(ttft), "tpot_ms": str(tpot),
            "completion_tokens": str(tokens), "est_cost_usd": str(cost),
            "concurrency": str(conc)}


class PoolSummaryTest(unittest.TestCase):
    def test_percentiles_cost_and_goodput(self):
        rows = [row(i * 0.1, ttft=100 + i, tokens=100, cost=0.0001)
                for i in range(100)]
        s = summarize.pool_summary(rows)["vllm-l4"]
        self.assertEqual(s["requests"], 100)
        self.assertEqual(s["errors"], 0)
        self.assertEqual(s["ttft_ms"]["p50"], 149.0)   # nearest-rank
        self.assertEqual(s["ttft_ms"]["p99"], 198.0)
        # 100 * 0.0001 USD / 10_000 tokens = $1.00 per 1M
        self.assertAlmostEqual(s["usd_per_1m_output_tokens"], 1.0)
        # all rows meet SLO across a 9.9s span
        self.assertAlmostEqual(s["goodput_rps"], round(100 / 9.9, 2))
        self.assertTrue(s["slo_ttft_p99_met"])

    def test_slo_breaches_drop_goodput_not_requests(self):
        rows = ([row(i * 0.1) for i in range(50)] +
                [row(5 + i * 0.1, tpot=80.0) for i in range(50)])  # breaches
        s = summarize.pool_summary(rows)["vllm-l4"]
        self.assertEqual(s["requests"], 100)
        self.assertFalse(s["slo_tpot_p99_met"])
        span = summarize._span_seconds(rows)
        self.assertAlmostEqual(s["goodput_rps"], round(50 / span, 2))

    def test_errors_counted_and_excluded_from_latency(self):
        rows = [row(0.0), row(0.5, status="503", ttft="")]
        s = summarize.pool_summary(rows)["vllm-l4"]
        self.assertEqual(s["errors"], 1)
        self.assertEqual(s["ttft_ms"]["p99"], 100.0)


class GoodputCurveTest(unittest.TestCase):
    def test_curve_rises_then_saturates(self):
        rows = []
        t = 0.0
        # conc 2: 20 good requests over 10s; conc 8: 44 good + 36 breaching
        for i in range(20):
            rows.append(row(t + i * 0.5, conc=2))
        t = 100.0
        for i in range(80):
            rows.append(row(t + i * 0.125, conc=8,
                            tpot=25.0 if i % 2 == 0 or i < 8 else 80.0))
        curves = summarize.goodput_curve(rows)
        blended = {p["conc"]: p["tps"] for p in curves["blended"]["points"]}
        self.assertLess(blended[2], blended[8])
        self.assertIn("vllm-l4", curves)
        self.assertGreater(curves["blended"]["slo_max_conc"], 0)


if __name__ == "__main__":
    unittest.main()
