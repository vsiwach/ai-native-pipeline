"""The policy engine — pure decision logic, no I/O. Given registry, policy,
and health state, pick the endpoint for a request. Unit-test this hard."""

from dataclasses import dataclass


class UnknownModel(Exception):
    pass


class NoHealthyBackend(Exception):
    pass


@dataclass
class Choice:
    model: str
    tier: str
    provider: str
    url: str
    est_cost_usd: float  # per single request
    queued: bool = False


def resolve_tier(model: str, tier_param: str | None,
                 registry: dict, policy: dict) -> str:
    """Explicit ?tier= wins; unknown tiers fall back to the backend's
    registry tier; otherwise the registry tier is the default."""
    backend = registry.get(model)
    if backend is None:
        raise UnknownModel(model)
    registry_tier = backend.get("tier", "standard")
    if tier_param and tier_param in policy["tiers"]:
        return tier_param
    return registry_tier


def select(model: str, tier_param: str | None, registry: dict, policy: dict,
           health_status_for) -> Choice:
    """health_status_for: (url) -> EndpointHealth (see health.py)."""
    tier = resolve_tier(model, tier_param, registry, policy)
    tier_rules = policy["tiers"].get(tier, {})
    cost_table = policy["cost_table"]

    candidates = [
        ep for ep in policy["endpoints"].get(model, [])
        if health_status_for(ep["url"]).usable
    ]
    if not candidates:
        raise NoHealthyBackend(model)

    def per_request_cost(ep: dict) -> float:
        return float(cost_table.get(ep["provider"], 0.0)) / 1_000_000

    if tier_rules.get("prefer") == "lowest_latency":
        # endpoints never measured sort last among themselves by cost
        def latency_key(ep):
            p50 = health_status_for(ep["url"]).p50_ms
            return (p50 is None, p50 or 0.0, per_request_cost(ep))
        chosen = min(candidates, key=latency_key)
    else:  # lowest_cost is the default preference
        chosen = min(candidates, key=lambda ep: (per_request_cost(ep),
                                                 ep["provider"]))

    return Choice(
        model=model,
        tier=tier,
        provider=chosen["provider"],
        url=chosen["url"],
        est_cost_usd=per_request_cost(chosen),
        queued=bool(tier_rules.get("queue", False)),
    )
