"""The policy engine — pure decision logic, no I/O. Given registry, policy,
and health state, pick the endpoint (Phase 3) or the stateful replica (Phase 7)
for a request. Unit-test this hard."""

from dataclasses import dataclass

from router_app.affinity import ConsistentHashRing, prefix_hash


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


# --------------------------------------------------------------------------
# Phase 7 — stateful, KV/prefix-aware replica selection.
# --------------------------------------------------------------------------

@dataclass
class ReplicaChoice:
    replica_id: str
    provider: str
    url: str
    prefix: str
    cache_hit: bool       # chosen replica already holds this prefix's KV
    reason: str           # which layer decided — for the event log / devboard


def select_replica(prompt, candidates, *, is_usable, kvstate, tier_rules,
                   cost_of, affinity_cfg, capacity=8, latency_of=None,
                   placement_filter=None, now=None) -> ReplicaChoice:
    """Layered decision (each layer narrows, the next breaks ties):

      1. placement filter   region / compliance eligibility (Phase 8 hook)
      2. prefix affinity     consistent-hash the prompt prefix to a replica
                             that holds (or should hold) its KV
      3. least-pending       skip replicas at/over capacity; among ties prefer
                             fewer in-flight requests
      4. tier preference     lowest_cost | lowest_latency as the final tiebreak

    Pure: all state is injected (`is_usable`, `kvstate`, `cost_of`,
    `latency_of`). `candidates` is a list of {id, provider, url, ...} dicts.
    """
    candidates = [c for c in candidates
                  if placement_filter is None or placement_filter(c)]
    if not candidates:
        raise NoHealthyBackend("no candidate replica passes placement policy")

    def healthy_and_free(c):
        return is_usable(c["url"]) and kvstate.pending(c["id"]) < capacity

    eligible = [c for c in candidates if healthy_and_free(c)]
    if not eligible:
        # everyone healthy is full, or all unhealthy — fall back to any healthy
        eligible = [c for c in candidates if is_usable(c["url"])]
    if not eligible:
        raise NoHealthyBackend("no healthy replica for request")

    prefix = prefix_hash(prompt, affinity_cfg.get("prefix_tokens", 32))
    by_id = {c["id"]: c for c in eligible}

    if affinity_cfg.get("enabled"):
        # ring over ALL candidate ids (not just eligible) so a health flap on
        # one replica never reshuffles another's prefixes — we just skip it.
        ring = ConsistentHashRing([c["id"] for c in candidates])
        order = [by_id[r] for r in ring.preference(prefix) if r in by_id]
        # 2a. warm wins: a replica already holding this prefix turns an
        #     expensive prefill into a cache hit. Among holders, the
        #     ring-preferred one keeps placement stable.
        holders = [c for c in order if kvstate.holds(c["id"], prefix, now)]
        if holders:
            chosen, reason = holders[0], "affinity_warm"
        elif order:
            # 2b. new prefix: stable consistent-hash placement (its future home)
            chosen, reason = order[0], "affinity_place"
        else:  # ring owners all ineligible — fall through to load/tier
            chosen = _least_pending_then_tier(eligible, kvstate, tier_rules,
                                              cost_of, latency_of)
            reason = "least_pending_fallback"
    else:
        chosen = _least_pending_then_tier(eligible, kvstate, tier_rules,
                                          cost_of, latency_of)
        reason = "least_pending"

    cache_hit = kvstate.holds(chosen["id"], prefix, now)
    return ReplicaChoice(replica_id=chosen["id"], provider=chosen["provider"],
                         url=chosen["url"], prefix=prefix, cache_hit=cache_hit,
                         reason=reason)


def _least_pending_then_tier(eligible, kvstate, tier_rules, cost_of, latency_of):
    prefer = tier_rules.get("prefer", "lowest_cost")

    def tier_key(c):
        if prefer == "lowest_latency" and latency_of is not None:
            p50 = latency_of(c["url"])
            return (p50 is None, p50 or 0.0, cost_of(c["provider"]))
        return (cost_of(c["provider"]), c["provider"])

    return min(eligible, key=lambda c: (kvstate.pending(c["id"]), tier_key(c)))
