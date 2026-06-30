"""Pure affinity primitives: prefix hashing + consistent-hash ring stability."""

from router_app.affinity import ConsistentHashRing, prefix_hash


def test_shared_prefix_collides():
    a = "the quick brown fox jumps over the lazy dog and runs on and on forever"
    b = "the quick brown fox jumps over the lazy dog but stops here abruptly now"
    assert prefix_hash(a, 8) == prefix_hash(b, 8)
    assert prefix_hash(a, 64) != prefix_hash(b, 64)


def test_preference_is_deterministic():
    ring = ConsistentHashRing(["r0", "r1", "r2"])
    assert ring.preference("abc") == ring.preference("abc")
    assert set(ring.preference("abc")) == {"r0", "r1", "r2"}


def test_owner_stable_when_unrelated_replica_added():
    """Consistent hashing: adding a replica must not move most keys."""
    before = ConsistentHashRing(["r0", "r1", "r2"])
    after = ConsistentHashRing(["r0", "r1", "r2", "r3"])
    keys = [f"prefix-{i}" for i in range(200)]
    moved = sum(1 for k in keys
                if before.preference(k)[0] != after.preference(k)[0])
    # with 4 replicas, ideal reassignment is ~1/4; allow generous slack but
    # prove it is NOT a full reshuffle.
    assert moved < len(keys) * 0.5


def test_removing_replica_relands_consistently():
    full = ConsistentHashRing(["r0", "r1", "r2"])
    key = "stable-prefix"
    owner = full.preference(key)[0]
    without = ConsistentHashRing([r for r in ["r0", "r1", "r2"] if r != owner])
    # the re-landing target is deterministic and equals full's 2nd choice
    assert without.preference(key)[0] == full.preference(key)[1]
