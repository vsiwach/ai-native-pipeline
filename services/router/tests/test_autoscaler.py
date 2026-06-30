"""Cold-start-aware autoscaler — deterministic control-logic tests."""

from router_app.autoscaler import (DRAINING, WARM, WARMING, AutoScaler,
                                    AutoscaleConfig, Fleet, Replica)


def _scaler(**cfg):
    events = []
    cfg.setdefault("cold_start_s", 8.0)
    sc = AutoScaler(AutoscaleConfig(**cfg), emit=lambda k, **f: events.append((k, f)))
    return sc, events


def test_promote_after_cold_start():
    sc, _ = _scaler()
    sc.step(now=0.0, pending=4)               # starts one warming replica
    assert sc.fleet.count(WARMING) == 1
    sc.step(now=8.0, pending=4)               # cold start elapsed → promote
    assert sc.fleet.count(WARM) == 1


def test_idle_scales_to_zero():
    sc, _ = _scaler(min_warm=0, idle_timeout_s=30.0)
    sc.step(0.0, pending=4)
    sc.step(8.0, pending=4)                    # warm
    assert sc.fleet.count(WARM) == 1
    # traffic stops; advance past idle timeout
    sc.step(40.0, pending=0)                   # drains
    sc.step(41.0, pending=0)                   # stops (removed)
    assert sc.fleet.count(WARM, WARMING, DRAINING) == 0


def test_burst_uses_warm_pool_and_reports_cold_start_avoided():
    sc, _ = _scaler(min_warm=1, max_replicas=3, target_pending_per_replica=2)
    # establish the warm pool (min_warm=1)
    sc.step(0.0, pending=0)
    sc.step(8.0, pending=0)
    assert sc.warm_available() is True
    # a burst arrives — needs ceil(6/2)=3 replicas; 1 already warm absorbs first
    decisions = sc.step(8.0, pending=6)
    starts = [d for d in decisions if d["action"] == "start"]
    assert starts, "burst should start more replicas"
    assert any(d["cold_start_avoided_ms"] > 0 for d in starts), \
        "warm pool should let the burst avoid a cold start"
    assert sc.fleet.count(WARM, WARMING) == 3


def test_respects_max_replicas():
    sc, _ = _scaler(max_replicas=2, target_pending_per_replica=1)
    sc.step(0.0, pending=100)
    assert sc.fleet.count(WARMING) == 2       # capped


def test_predictive_prewarm_raises_desired_before_traffic():
    sc = AutoScaler(AutoscaleConfig(min_warm=0, target_pending_per_replica=4),
                    forecast=lambda now: 8)   # forecast says a burst is coming
    sc.step(0.0, pending=0)                    # no real demand yet
    assert sc.fleet.count(WARMING) == 2        # ceil(8/4) pre-warmed


def test_decisions_are_emitted_as_events():
    sc, events = _scaler()
    sc.step(0.0, pending=4)
    assert any(kind == "scale" for kind, _ in events)
