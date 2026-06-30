"""Reliability: stuck-replica detection + recovery, region failover, and the
release engine (canary/shadow/A-B, drain, probe gates, auto-rollback)."""

import pytest

from router_app.failover import NoRegionAvailable, choose_region
from router_app.health import HealthPoller
from router_app.release import (AB, CANARY, COMPLETE, IN_PROGRESS, ROLLED_BACK,
                                SHADOW, Release, can_stop_drained)


# ---------------------------------------------------------------- stuck replica
def test_stuck_replica_detected_ejected_and_recovers():
    poller = HealthPoller(get_endpoints=lambda: {})
    url = "http://r0"
    poller.record_latency(url, 10.0)            # healthy, serving
    poller.record_progress(url, now=0.0)        # last token progress at t=0
    assert poller.status_for(url).usable is True

    ejected = poller.detect_stuck(now=31.0, deadline_s=30.0)  # no progress 31s
    assert url in ejected
    assert poller.status_for(url).usable is False             # ejected
    assert poller.degraded() is True

    # a later successful health poll recovers it (simulate poll result)
    s = poller.status_for(url)
    s.ejected, s.healthy, s.last_progress = False, True, None
    assert poller.status_for(url).usable is True


def test_slow_but_progressing_replica_is_not_stuck():
    poller = HealthPoller(get_endpoints=lambda: {})
    poller.record_progress("http://r0", now=100.0)
    assert poller.detect_stuck(now=110.0, deadline_s=30.0) == []


# ------------------------------------------------------------------- failover
REGION_POLICY = {"active": ["us-central1", "us-east-1"],
                 "fallback": ["eu-west-1"]}


def test_routes_to_home_region_when_healthy():
    c = choose_region("us-east-1", REGION_POLICY,
                      is_region_healthy=lambda r: True)
    assert c.region == "us-east-1" and c.failed_over is False


def test_fails_over_when_region_down():
    down = {"us-central1"}
    c = choose_region("us-central1", REGION_POLICY,
                      is_region_healthy=lambda r: r not in down)
    assert c.region == "us-east-1" and c.failed_over is True


def test_falls_back_to_passive_region_when_all_active_down():
    down = {"us-central1", "us-east-1"}
    c = choose_region("us-central1", REGION_POLICY,
                      is_region_healthy=lambda r: r not in down)
    assert c.region == "eu-west-1"


def test_failover_prefers_within_slo_region():
    c = choose_region("us-central1", REGION_POLICY,
                      is_region_healthy=lambda r: True,
                      latency_ms_of=lambda r: 50 if r == "us-east-1" else 5000,
                      slo_ms=250)
    assert c.region == "us-east-1" and c.within_slo is True


def test_no_healthy_region_raises():
    with pytest.raises(NoRegionAvailable):
        choose_region("us-central1", REGION_POLICY,
                      is_region_healthy=lambda r: False)


# ------------------------------------------------------------- release engine
def test_canary_shifts_5_25_100_with_probe_gate():
    rel = Release("v1", "v2", mode=CANARY, steps=(5, 25, 100))
    rel.start()
    assert rel.candidate_weight == 5
    assert rel.advance(probe_ok=True)["weight"] == 25
    assert rel.advance(probe_ok=True)["weight"] == 100
    assert rel.state == COMPLETE


def test_canary_auto_rolls_back_on_probe_breach():
    rel = Release("v1", "v2", steps=(5, 25, 100))
    rel.start()
    rel.advance(probe_ok=True)                 # at 25%
    ev = rel.advance(probe_ok=False)           # SLO breach
    assert rel.state == ROLLED_BACK
    assert ev["reason"] == "probe_failed"
    assert rel.candidate_weight == 0           # all traffic back to stable
    assert rel.route("any-key") == "v1"


def test_canary_split_is_deterministic_and_weighted():
    rel = Release("v1", "v2", steps=(25, 100))
    rel.start()                                # 25%
    keys = [f"req-{i}" for i in range(1000)]
    to_candidate = sum(1 for k in keys if rel.route(k) == "v2")
    assert 200 <= to_candidate <= 300          # ~25%
    # deterministic: same key, same routing
    assert all(rel.route(k) == rel.route(k) for k in keys[:50])


def test_shadow_never_shifts_client_traffic_but_mirrors():
    rel = Release("v1", "v2", mode=SHADOW, steps=(0,))
    rel.start()
    assert all(rel.route(f"k{i}") == "v1" for i in range(100))  # client sees stable
    assert rel.mirror_to_candidate("k1") is True                # candidate mirrored


def test_warmup_before_shift_and_drain_on_complete():
    rel = Release("v1", "v2", steps=(50, 100), warmup=True, drain=True)
    start = rel.start()
    assert start["warmups"] == ["v2"]          # candidate warmed before traffic
    done = rel.advance(probe_ok=True)
    assert done["state"] == COMPLETE and done["drains"] == ["v1"]


def test_rolling_deploy_is_lossless_drain_waits_for_inflight():
    # an in-flight request on the draining stable replica must not be dropped
    pending = 1
    assert can_stop_drained(pending) is False   # cannot stop with in-flight
    pending = 0                                  # request finished
    assert can_stop_drained(pending) is True     # now safe to stop


def test_ab_mode_counts_both_versions():
    rel = Release("v1", "v2", mode=AB, steps=(50,))
    rel.start()
    seen = {rel.route(f"k{i}") for i in range(200)}
    assert seen == {"v1", "v2"}
