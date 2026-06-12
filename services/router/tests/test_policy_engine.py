"""Unit tests for the pure policy engine — per the phase prompt, tested hard:
tier resolution/fallback, unhealthy skip, cost vs latency preference."""

import pytest

from router_app.health import EndpointHealth
from router_app.policy import (NoHealthyBackend, UnknownModel, resolve_tier,
                               select)

REGISTRY = {"house-price-reg": {"tier": "standard", "target": "cpu"}}
POLICY = {
    "tiers": {
        "realtime": {"max_latency_ms": 250, "prefer": "lowest_latency"},
        "standard": {"max_latency_ms": 2000, "prefer": "lowest_cost"},
        "batch": {"max_latency_ms": None, "prefer": "lowest_cost",
                  "queue": True},
    },
    "cost_table": {"gcp-cloudrun-cpu": 0.40, "aws-apprunner-cpu": 0.46},
    "endpoints": {
        "house-price-reg": [
            {"provider": "gcp-cloudrun-cpu", "url": "http://gcp"},
            {"provider": "aws-apprunner-cpu", "url": "http://aws"},
        ]
    },
}


class FakeHealth:
    def __init__(self):
        self.status: dict[str, EndpointHealth] = {}

    def __call__(self, url):
        return self.status.setdefault(url, EndpointHealth())

    def set(self, url, healthy=True, latencies=()):
        s = self(url)
        s.healthy = healthy
        s.latencies_ms.extend(latencies)


@pytest.fixture()
def health():
    return FakeHealth()


class TestTierResolution:
    def test_defaults_to_registry_tier(self):
        assert resolve_tier("house-price-reg", None, REGISTRY, POLICY) == "standard"

    def test_explicit_tier_wins(self):
        assert resolve_tier("house-price-reg", "batch", REGISTRY, POLICY) == "batch"

    def test_unknown_tier_falls_back_to_registry_tier(self):
        assert resolve_tier("house-price-reg", "warp", REGISTRY, POLICY) == "standard"

    def test_unknown_model_raises(self):
        with pytest.raises(UnknownModel):
            resolve_tier("nope", None, REGISTRY, POLICY)


class TestSelection:
    def test_lowest_cost_picks_cheaper_cloud(self, health):
        choice = select("house-price-reg", "standard", REGISTRY, POLICY, health)
        assert choice.provider == "gcp-cloudrun-cpu"  # 0.40 < 0.46
        assert choice.est_cost_usd == pytest.approx(0.40 / 1_000_000)

    def test_cost_arithmetic_per_request(self, health):
        choice = select("house-price-reg", "standard", REGISTRY, POLICY, health)
        # $0.40 per 1M requests -> $4e-7 per request
        assert choice.est_cost_usd == pytest.approx(4e-7)

    def test_unhealthy_backend_skipped(self, health):
        health.set("http://gcp", healthy=False)
        choice = select("house-price-reg", "standard", REGISTRY, POLICY, health)
        assert choice.provider == "aws-apprunner-cpu"

    def test_all_unhealthy_raises(self, health):
        health.set("http://gcp", healthy=False)
        health.set("http://aws", healthy=False)
        with pytest.raises(NoHealthyBackend):
            select("house-price-reg", "standard", REGISTRY, POLICY, health)

    def test_never_polled_is_optimistically_usable(self, health):
        choice = select("house-price-reg", "standard", REGISTRY, POLICY, health)
        assert choice is not None

    def test_lowest_latency_uses_p50(self, health):
        health.set("http://gcp", latencies=[100, 120, 110])   # p50 = 110
        health.set("http://aws", latencies=[40, 60, 50])      # p50 = 50
        choice = select("house-price-reg", "realtime", REGISTRY, POLICY, health)
        assert choice.provider == "aws-apprunner-cpu"

    def test_lowest_latency_prefers_measured_over_unmeasured(self, health):
        health.set("http://aws", latencies=[500])
        choice = select("house-price-reg", "realtime", REGISTRY, POLICY, health)
        assert choice.provider == "aws-apprunner-cpu"

    def test_batch_tier_flags_queue(self, health):
        choice = select("house-price-reg", "batch", REGISTRY, POLICY, health)
        assert choice.queued is True

    def test_unknown_model_raises_in_select(self, health):
        with pytest.raises(UnknownModel):
            select("nope", None, REGISTRY, POLICY, health)
