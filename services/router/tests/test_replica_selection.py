"""The layered, KV/prefix-aware replica selection — the heart of router v2.
Deterministic, I/O-free (state injected), exactly like policy.select."""

import pytest

from router_app.kvstate import KVState
from router_app.policy import NoHealthyBackend, select_replica

REPLICAS = [
    {"id": "r0", "provider": "local-docker", "url": "http://r0"},
    {"id": "r1", "provider": "local-docker", "url": "http://r1"},
    {"id": "r2", "provider": "local-docker", "url": "http://r2"},
]
AFFINITY = {"enabled": True, "prefix_tokens": 8, "capacity": 4}
TIER = {"prefer": "lowest_cost"}


def _kv():
    return KVState(kv_ttl_s=300.0, clock=lambda: 0.0)


def _select(prompt, *, kv, usable=None, affinity=AFFINITY, capacity=4):
    healthy = usable or (lambda u: True)
    return select_replica(
        prompt, REPLICAS, is_usable=healthy, kvstate=kv, tier_rules=TIER,
        cost_of=lambda p: 0.10, affinity_cfg=affinity, capacity=capacity,
        now=0.0)


def test_identical_prefix_routes_to_same_replica():
    kv = _kv()
    a = _select("shared prefix tokens here, request A diverges later", kv=kv)
    b = _select("shared prefix tokens here, request B diverges later", kv=kv)
    assert a.replica_id == b.replica_id


def test_warm_replica_holding_prefix_beats_cold():
    kv = _kv()
    prompt = "explain the kv cache and prefix reuse in detail please now"
    first = _select(prompt, kv=kv)            # placed (cold) → records prefix
    kv.record_prefix(first.replica_id, first.prefix, now=0.0)
    again = _select(prompt, kv=kv)            # now a warm cache hit
    assert again.replica_id == first.replica_id
    assert again.cache_hit is True
    assert again.reason == "affinity_warm"


def test_unhealthy_replica_relands_consistently():
    kv = _kv()
    prompt = "route me somewhere stable across health flaps consistently ok"
    owner = _select(prompt, kv=kv).replica_id

    down = lambda u: u != f"http://{owner}"
    relanded = _select(prompt, kv=kv, usable=down).replica_id
    assert relanded != owner
    # re-landing is consistent: same target every time the owner is down
    assert _select(prompt, kv=kv, usable=down).replica_id == relanded


def test_capacity_overflow_picks_next_ring_replica():
    kv = _kv()
    prompt = "a busy prefix whose owner is saturated with in-flight requests"
    owner = _select(prompt, kv=kv).replica_id
    for _ in range(4):  # fill the owner to capacity (4)
        kv.inc_pending(owner)
    overflow = _select(prompt, kv=kv, capacity=4).replica_id
    assert overflow != owner


def test_affinity_off_uses_least_pending():
    kv = _kv()
    # r0 busy, r1/r2 idle → least-pending should avoid r0
    kv.inc_pending("r0"); kv.inc_pending("r0")
    choice = _select("anything", kv=kv,
                     affinity={"enabled": False, "prefix_tokens": 8})
    assert choice.replica_id in ("r1", "r2")
    assert choice.reason == "least_pending"


def test_no_healthy_replica_raises():
    kv = _kv()
    with pytest.raises(NoHealthyBackend):
        _select("x", kv=kv, usable=lambda u: False)
