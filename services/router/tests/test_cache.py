from router_app.cache import TTLCache, cache_key


def test_key_is_stable_across_key_order():
    assert cache_key("m", {"a": 1, "b": 2}) == cache_key("m", {"b": 2, "a": 1})


def test_key_differs_by_model_and_payload():
    assert cache_key("m1", {"a": 1}) != cache_key("m2", {"a": 1})
    assert cache_key("m", {"a": 1}) != cache_key("m", {"a": 2})


def test_hit_and_miss_accounting():
    c = TTLCache(ttl_s=60)
    assert c.get("k") is None
    c.put("k", b"v")
    assert c.get("k") == b"v"
    assert (c.hits, c.misses) == (1, 1)
    assert c.hit_rate == 0.5


def test_expiry():
    c = TTLCache(ttl_s=-1)  # everything already expired
    c.put("k", b"v")
    assert c.get("k") is None


def test_disabled_cache_never_stores():
    c = TTLCache(ttl_s=60, enabled=False)
    c.put("k", b"v")
    assert c.get("k") is None
    assert (c.hits, c.misses) == (0, 0)
