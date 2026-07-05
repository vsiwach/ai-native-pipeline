"""loadgen planning logic — pure, seeded, no sockets: same seed -> same
schedule, mixes normalize and validate, percentiles/summary behave."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import loadgen  # noqa: E402

QS = ["q one?", "q two?", "q three?"]
MIX = [("docs-agent", 0.7), ("voice", 0.3)]


class PlanTest(unittest.TestCase):
    def test_same_seed_same_plan(self):
        a = loadgen.plan(42, 30, 2.0, 0.5, MIX, QS)
        b = loadgen.plan(42, 30, 2.0, 0.5, MIX, QS)
        self.assertEqual(a, b)
        self.assertGreater(len(a), 0)

    def test_different_seed_different_plan(self):
        a = loadgen.plan(42, 30, 2.0, 0.5, MIX, QS)
        b = loadgen.plan(43, 30, 2.0, 0.5, MIX, QS)
        self.assertNotEqual(a, b)

    def test_rate_is_roughly_rps(self):
        reqs = loadgen.plan(7, 300, 2.0, 0.5, MIX, QS)
        self.assertAlmostEqual(len(reqs) / 300, 2.0, delta=0.4)

    def test_offsets_sorted_within_duration(self):
        reqs = loadgen.plan(1, 30, 3.0, 0.5, MIX, QS)
        offsets = [r.t_offset_s for r in reqs]
        self.assertEqual(offsets, sorted(offsets))
        self.assertLess(offsets[-1], 30)

    def test_stream_ratio_extremes(self):
        all_stream = loadgen.plan(5, 60, 2.0, 1.0, MIX, QS)
        none_stream = loadgen.plan(5, 60, 2.0, 0.0, MIX, QS)
        self.assertTrue(all(r.stream for r in all_stream))
        self.assertTrue(not any(r.stream for r in none_stream))

    def test_profiles_and_tokens_from_mix(self):
        reqs = loadgen.plan(9, 120, 2.0, 0.5, [("voice", 1.0)], QS)
        self.assertTrue(all(r.profile == "voice" for r in reqs))
        self.assertTrue(all(
            r.max_tokens == loadgen.PROFILES["voice"]["max_tokens"]
            for r in reqs))

    def test_empty_questions_rejected(self):
        with self.assertRaises(ValueError):
            loadgen.plan(1, 10, 1.0, 0.5, MIX, [])


class MixTest(unittest.TestCase):
    def test_normalizes_weights(self):
        mix = loadgen.parse_mix("docs-agent=3,voice=1")
        self.assertAlmostEqual(sum(w for _, w in mix), 1.0)
        self.assertAlmostEqual(dict(mix)["docs-agent"], 0.75)

    def test_default_weight_is_one(self):
        mix = loadgen.parse_mix("docs-agent,voice")
        self.assertAlmostEqual(dict(mix)["voice"], 0.5)

    def test_unknown_profile_rejected(self):
        with self.assertRaises(ValueError):
            loadgen.parse_mix("gpu-goblin=1")

    def test_nonpositive_weight_rejected(self):
        with self.assertRaises(ValueError):
            loadgen.parse_mix("voice=0")


class SummaryTest(unittest.TestCase):
    def test_summarize_counts_and_percentiles(self):
        rows = [
            {"status": 200, "ttft_ms": 10.0, "total_ms": 50.0, "stream": True},
            {"status": 200, "ttft_ms": 20.0, "total_ms": 60.0, "stream": False},
            {"status": 500, "ttft_ms": None, "total_ms": 5.0, "stream": False},
        ]
        s = loadgen.summarize(rows)
        self.assertEqual((s["sent"], s["ok"], s["errors"]), (3, 2, 1))
        self.assertEqual(s["streamed"], 1)
        self.assertEqual(s["p50_ttft_ms"], 20.0)

    def test_pct_empty(self):
        self.assertIsNone(loadgen.pct([], 99))


if __name__ == "__main__":
    unittest.main()
