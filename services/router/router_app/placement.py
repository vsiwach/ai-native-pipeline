"""Placement policy — pure functions deciding WHICH capacity a request may use.

This is layer 1 of replica selection (before affinity). Two rules:

  - A compliance-bound request (it declares a `compliance` regime) may ONLY
    land on capacity tagged sensitive that satisfies that regime — it is
    DENIED ordinary capacity.
  - On sensitive capacity, compliance-bound work has RIGHT OF WAY: if the pool
    is full of non-compliant (filler) work, that work is preempted; if it is
    full of other compliant work, the request queues.

Pure: callers pass the policy dict and the current occupants; no I/O.
"""

ADMIT, PREEMPT, QUEUE, DENY = "admit", "preempt", "queue", "deny"


def _sensitive_tags(policy: dict) -> set:
    return set(policy.get("compliance", {}).get("sensitive_capacity_tags", []))


def is_sensitive(pool: dict, policy: dict) -> bool:
    return bool(set(pool.get("tags", [])) & _sensitive_tags(policy))


def eligible_pools(request: dict, policy: dict) -> list[dict]:
    """Pools this request may use, ordered by `capacity_preference`.

    request: {region?: str, compliance?: regime|None}. A compliance request
    gets only matching sensitive pools (ordinary capacity is excluded); a
    non-compliant request prefers ordinary pools, with sensitive pools allowed
    only as preemptible filler (ranked last)."""
    pools = policy.get("pools", [])
    regime = request.get("compliance")
    region = request.get("region")

    if regime:
        eligible = [p for p in pools
                    if regime in p.get("compliance_regimes", [])]
    else:
        eligible = list(pools)  # all, but sensitive ranked last below

    pref = policy.get("capacity_preference", ["cheapest"])
    primary = pref[0] if pref else "cheapest"

    def rank(p):
        # one stable key: in-region first, then non-sensitive (for filler),
        # then the capacity preference (cheapest / lowest cold start).
        out_of_region = 1 if region and p.get("region") != region else 0
        sensitive_last = (0 if regime else (1 if is_sensitive(p, policy) else 0))
        pref_key = (p.get("cold_start_s", 0) if primary == "lowest_latency"
                    else p.get("cost_rank", 0))
        return (out_of_region, sensitive_last, pref_key)

    return sorted(eligible, key=rank)


def plan_admission(request: dict, pool: dict, occupants: list[dict], *,
                   capacity: int, policy: dict) -> dict:
    """Decide how `request` is admitted to `pool` given current `occupants`
    (each {id, compliance}). Returns {action, victim?}."""
    regime = request.get("compliance")

    # a compliance request must never be placed on non-matching capacity
    if regime and regime not in pool.get("compliance_regimes", []):
        return {"action": DENY, "reason": "pool does not satisfy regime"}

    if len(occupants) < capacity:
        return {"action": ADMIT}

    # pool is full — right-of-way for compliance work on sensitive capacity
    if regime and is_sensitive(pool, policy):
        filler = [o for o in occupants if not o.get("compliance")]
        if filler:
            return {"action": PREEMPT, "victim": filler[0]["id"],
                    "reason": "compliance right-of-way over non-compliant work"}
        return {"action": QUEUE, "reason": "all occupants are compliance-bound"}

    return {"action": QUEUE, "reason": "pool at capacity"}
