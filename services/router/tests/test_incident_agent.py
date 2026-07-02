"""IncidentAgentLogic — pure decision core, driven with synthetic signals."""

import unittest

from router_app.incident_agent import (AgentConfig, IncidentAgentLogic,
                                       PoolSignal)


def sig(pool="vllm-l4", usable=True, healthz=True, breach=0.0, n=10):
    return PoolSignal(pool_id=pool, url=f"http://{pool}:8080", usable=usable,
                      healthz_ok=healthz, breach_rate=breach, samples=n)


def ops(effects):
    return [e["op"] for e in effects]


class DetectionTest(unittest.TestCase):
    def setUp(self):
        self.logic = IncidentAgentLogic(AgentConfig())

    def test_healthy_signals_do_nothing(self):
        self.assertEqual(self.logic.step(0.0, [sig(), sig("baseten-l4")], 2),
                         [])

    def test_breach_opens_quarantines_and_spills(self):
        effects = self.logic.step(
            0.0, [sig(breach=0.8), sig("baseten-l4")], 2)
        self.assertEqual(ops(effects),
                         ["open", "act", "quarantine", "act"])
        self.assertIn("80%", effects[0]["title"])
        self.assertTrue(self.logic.cases["vllm-l4"].quarantined)

    def test_last_healthy_pool_is_never_quarantined(self):
        effects = self.logic.step(0.0, [sig(breach=1.0, n=10)], healthy_pools=1)
        self.assertEqual(ops(effects), ["open", "act"])
        self.assertIn("quarantine withheld", effects[0]["title"])
        self.assertFalse(self.logic.cases["vllm-l4"].quarantined)

    def test_pool_down_beats_breach_classification(self):
        effects = self.logic.step(0.0, [sig(healthz=False, usable=False,
                                            breach=1.0), sig("baseten-l4")], 1)
        self.assertEqual(effects[0]["op"], "open")
        self.assertEqual(self.logic.cases["vllm-l4"].kind, "pool_down")

    def test_too_few_samples_no_incident(self):
        self.assertEqual(
            self.logic.step(0.0, [sig(breach=1.0, n=2), sig("b")], 2), [])


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.cfg = AgentConfig(probe_interval_s=3.0, probes_to_reinstate=2,
                               cooldown_s=30.0)
        self.logic = IncidentAgentLogic(self.cfg)
        self.logic.step(0.0, [sig(breach=0.9), sig("baseten-l4")], 2)

    def test_probes_fire_on_interval(self):
        self.assertEqual(ops(self.logic.step(1.0, [sig(breach=0.9),
                                                   sig("baseten-l4")], 1)), [])
        effects = self.logic.step(3.5, [sig(breach=0.9), sig("baseten-l4")], 1)
        self.assertEqual(ops(effects), ["probe"])

    def test_two_passing_probes_reinstate_and_resolve(self):
        e1 = self.logic.record_probe(4.0, "vllm-l4", ok=True, latency_ms=90)
        self.assertEqual(ops(e1), ["act"])
        e2 = self.logic.record_probe(7.0, "vllm-l4", ok=True, latency_ms=85)
        self.assertEqual(ops(e2), ["act", "reinstate", "act", "resolve"])
        self.assertNotIn("vllm-l4", self.logic.cases)

    def test_failed_probe_resets_the_streak(self):
        self.logic.record_probe(4.0, "vllm-l4", ok=True, latency_ms=90)
        self.logic.record_probe(7.0, "vllm-l4", ok=False, latency_ms=1600)
        e = self.logic.record_probe(10.0, "vllm-l4", ok=True, latency_ms=88)
        self.assertEqual(ops(e), ["act"])          # streak back to 1, no resolve

    def test_cooldown_blocks_immediate_reopen(self):
        self.logic.record_probe(4.0, "vllm-l4", ok=True, latency_ms=90)
        self.logic.record_probe(7.0, "vllm-l4", ok=True, latency_ms=85)
        # still breaching right after resolve -> cooldown suppresses reopen
        self.assertEqual(
            self.logic.step(8.0, [sig(breach=0.9), sig("baseten-l4")], 2), [])
        effects = self.logic.step(38.0, [sig(breach=0.9),
                                         sig("baseten-l4")], 2)
        self.assertEqual(effects[0]["op"], "open")


class PoolDownRecoveryTest(unittest.TestCase):
    def test_pool_down_resolves_when_health_returns(self):
        logic = IncidentAgentLogic(AgentConfig())
        logic.step(0.0, [sig(healthz=False, usable=False),
                         sig("baseten-l4")], 2)
        self.assertTrue(logic.cases["vllm-l4"].quarantined)
        effects = logic.step(10.0, [sig(healthz=True, usable=False),
                                    sig("baseten-l4")], 1)
        self.assertEqual(ops(effects), ["reinstate", "act", "resolve"])


class SameTickRaceTest(unittest.TestCase):
    def test_two_pools_breaching_same_tick_never_both_quarantined(self):
        """The healthy count is a tick-start snapshot; without live
        decrementing, a chaos blast on every pool would quarantine ALL of
        them in one tick and zero the service."""
        logic = IncidentAgentLogic(AgentConfig())
        effects = logic.step(
            0.0, [sig("vllm-l4", breach=1.0), sig("baseten-l4", breach=1.0)],
            healthy_pools=2)
        quarantined = [e["pool_id"] for e in effects
                       if e["op"] == "quarantine"]
        self.assertEqual(quarantined, ["vllm-l4"])   # first only
        self.assertFalse(logic.cases["baseten-l4"].quarantined)
        # both incidents still opened — nothing failed silently
        self.assertEqual(len([e for e in effects if e["op"] == "open"]), 2)


class EscalationTest(unittest.TestCase):
    def test_persistent_probe_failures_escalate_once(self):
        cfg = AgentConfig(escalate_after_failures=3)
        logic = IncidentAgentLogic(cfg)
        logic.step(0.0, [sig(breach=1.0), sig("baseten-l4")], 2)
        for i in range(2):
            e = logic.record_probe(float(i), "vllm-l4", ok=False,
                                   latency_ms=900)
            self.assertNotIn("escalate", ops(e))
        e3 = logic.record_probe(9.0, "vllm-l4", ok=False, latency_ms=900)
        self.assertIn("escalate", ops(e3))
        # escalation fires exactly once; quarantine + probing continue
        e4 = logic.record_probe(12.0, "vllm-l4", ok=False, latency_ms=900)
        self.assertNotIn("escalate", ops(e4))
        self.assertTrue(logic.cases["vllm-l4"].quarantined)

    def test_recovery_after_escalation_still_resolves(self):
        cfg = AgentConfig(escalate_after_failures=2, probes_to_reinstate=2)
        logic = IncidentAgentLogic(cfg)
        logic.step(0.0, [sig(breach=1.0), sig("baseten-l4")], 2)
        logic.record_probe(1.0, "vllm-l4", ok=False, latency_ms=900)
        logic.record_probe(2.0, "vllm-l4", ok=False, latency_ms=900)
        logic.record_probe(3.0, "vllm-l4", ok=True, latency_ms=40)
        e = logic.record_probe(4.0, "vllm-l4", ok=True, latency_ms=45)
        self.assertIn("resolve", ops(e))
        self.assertNotIn("vllm-l4", logic.cases)


if __name__ == "__main__":
    unittest.main()
