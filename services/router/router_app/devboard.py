"""Devboard shape builders — contracts/devboard.openapi.yaml, exactly.

Pure functions over injected state (MetricsWindow, IncidentStore, health,
policy). The HTTP layer in main.py only glues these to routes; unit tests
drive them directly with synthetic samples. No fabricated values: empty
windows produce zeros/empties, never plausible-looking numbers.
"""

from router_app.metrics import MetricsWindow

# windows (seconds) — percentiles want stability, hero wants liveness
HERO_WINDOW_S = 60.0
SLO_WINDOW_S = 60.0
COST_WINDOW_S = 900.0
GOODPUT_OP_WINDOW_S = 10.0
SPARK_HOURS = 24


def _delta_pct(current: float, baseline: float) -> float:
    if baseline <= 0:
        return 0.0
    return round((current - baseline) / baseline * 100.0, 1)


def hero(metrics: MetricsWindow, incidents, tpot_slo_ms: float,
         now: float | None = None) -> dict:
    recent = metrics.window(HERO_WINDOW_S, now)
    tpot_sorted = sorted(s.tpot_ms for s in recent)
    from router_app.metrics import percentile
    tpot_p99 = round(percentile(tpot_sorted, 99), 1)

    cost_samples = metrics.window(COST_WINDOW_S, now)
    blended = MetricsWindow.cost_per_mtok(cost_samples)
    # "vs single-pool": what the same window would have cost on the priciest
    # pool alone (the managed pool without the cheap spill capacity)
    per_pool = {r: MetricsWindow.cost_per_mtok(ss)
                for r, ss in MetricsWindow.by_replica(cost_samples).items()
                if ss}
    single_pool = max(per_pool.values()) if len(per_pool) > 1 else blended

    spark_tpot = metrics.hourly_series(SPARK_HOURS, "tpot_ms", now)
    tpot_24h_ago = next((v for v in spark_tpot if v > 0), 0.0)

    mttr_agent = incidents.mttr_median(agent=True)
    mttr_manual = incidents.mttr_median(agent=False)

    return {
        "tpot_p99_ms": tpot_p99,
        "tpot_slo_ms": tpot_slo_ms,
        "tpot_delta_pct": _delta_pct(tpot_p99, tpot_24h_ago),
        "cost_per_mtok_usd": blended,
        "cost_delta_pct": _delta_pct(blended, single_pool),
        "mttr_s": mttr_agent,
        "mttr_delta_pct": _delta_pct(mttr_agent, mttr_manual),
        "spark": {
            "tpot": spark_tpot,
            "cost": metrics.hourly_cost_series(SPARK_HOURS, now),
            "mttr": _hourly_mttr(incidents, SPARK_HOURS, now),
        },
    }


def _hourly_mttr(incidents, hours: int, now: float | None) -> list[float]:
    import time
    now = now or time.time()
    buckets: list[list[float]] = [[] for _ in range(hours)]
    for inc in incidents.snapshot():
        if inc["live"]:
            continue
        age = now - inc["ts"]
        if 0 <= age < hours * 3600:
            buckets[int(age // 3600)].append(inc["mttr_s"])
    return list(reversed(
        [round(sum(b) / len(b), 1) if b else 0.0 for b in buckets]))


def _health_of(samples, usable: bool) -> tuple[float, str]:
    if not usable:
        return 0.0, "bad"
    rate = MetricsWindow.slo_rate(samples)
    health = round(rate * 100.0, 0)
    status = "ok" if health >= 90 else ("warn" if health >= 50 else "bad")
    return health, status


def slo_panel(metrics: MetricsWindow, replicas: list[dict], tier_rules: dict,
              is_usable, pending_of, goodput_curves: dict | None = None,
              now: float | None = None) -> dict:
    """/v1/metrics/slo — per-pool percentiles + hist; goodput curve comes from
    the bench harness artifact (real measured curve), operating point is live.
    """
    samples = metrics.window(SLO_WINDOW_S, now)
    by_replica = MetricsWindow.by_replica(samples)
    op_samples = metrics.window(GOODPUT_OP_WINDOW_S, now)
    pools = []
    for rep in replicas:
        rid = rep["id"]
        pool_samples = by_replica.get(rid, [])
        usable = is_usable(rep["url"])
        health, status = _health_of(pool_samples, usable)
        ttft = MetricsWindow.latency_stats(pool_samples, "ttft_ms")
        tpot = MetricsWindow.latency_stats(pool_samples, "tpot_ms")
        ttft["slo"] = tier_rules.get("ttft_ms", 0)
        tpot["slo"] = tier_rules.get("tpot_ms", 0)
        pool = {"id": rid, "health": health, "status": status,
                "ttft": ttft, "tpot": tpot}
        curve = (goodput_curves or {}).get(rid)
        pool_op = [s for s in op_samples if s.replica == rid and s.slo_met]
        operating = {
            "conc": pending_of(rid),
            "tps": round(len(pool_op) / GOODPUT_OP_WINDOW_S, 2),
        }
        if curve:
            pool["goodput"] = {"points": curve.get("points", []),
                               "operating": operating,
                               "slo_max_conc": curve.get("slo_max_conc", 0)}
        else:
            pool["goodput"] = {"points": [], "operating": operating}
        pools.append(pool)
    return {"pools": pools}


def pools_snapshot(metrics: MetricsWindow, replicas: list[dict],
                   registry_entry: dict, is_usable, pending_of,
                   capacity: int = 8, now: float | None = None) -> dict:
    samples = metrics.window(COST_WINDOW_S, now)
    by_replica = MetricsWindow.by_replica(samples)
    pools = []
    for rep in replicas:
        rid = rep["id"]
        pool_samples = by_replica.get(rid, [])
        usable = is_usable(rep["url"])
        health, status = _health_of(pool_samples, usable)
        util = min(100.0, round(pending_of(rid) / max(1, capacity) * 100, 1))
        if util > 90 and status == "ok":
            status = "warn"
        scale_to_zero = str(registry_entry.get("scale_to_zero",
                                               "true")).lower() == "true"
        pools.append({
            "id": rid,
            "hw": rep.get("provider", "unknown"),
            "health": health,
            "status": status,
            "util_pct": util,
            "cost_per_mtok": MetricsWindow.cost_per_mtok(pool_samples),
            "autoscaler": {
                # MVP: each policy endpoint is one replica; F2 swaps in the
                # live Baseten autoscaler state via the management API.
                "replicas": 1 if usable else 0,
                "min": 0 if scale_to_zero else 1,
                "max": int(registry_entry.get("max_replicas", 1)),
                "state": ("ejected" if not usable
                          else "saturated" if util > 90 else "steady"),
            },
        })
    return {"pools": pools}


def feed_item(event: dict) -> dict | None:
    """Map a router 'route' event to the placement-feed shape."""
    if event.get("kind") != "route" or "req" not in event:
        return None
    return {"req": event["req"], "tier": event.get("wl_tier", "agent"),
            "tag": event.get("tag"), "pool": event.get("replica", ""),
            "reason": event.get("reason", ""),
            "decide_ms": event.get("decide_ms", 0.0),
            "ts": event.get("iso_ts", "")}


def release_active(release, model: str) -> dict:
    """Active rollout state; a steady system reports its stable version at
    100% rather than inventing a canary."""
    if release is None:
        return {"version": "stable", "from": "stable", "to": "stable",
                "strategy": "steady", "model": model,
                "steps": [{"pct": "100%", "status": "pass"}]}
    steps = []
    for i, pct in enumerate(release.steps):
        if i < release.step_index or release.state == "complete":
            status = "pass"
        elif i == release.step_index:
            status = "fail" if release.state == "rolled_back" else "live"
        else:
            status = "wait"
        steps.append({"pct": f"{pct}%", "status": status})
        # gate verdicts (tpot_p99 vs threshold) land in F5 when the release
        # engine's probes carry measured values; omitted rather than faked.
    return {"version": release.candidate, "from": release.stable,
            "to": release.candidate, "strategy": release.mode,
            "model": model, "steps": steps}
