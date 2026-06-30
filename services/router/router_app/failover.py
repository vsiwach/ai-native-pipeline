"""Region-aware routing with active-active + fallback — pure logic.

Multi-region serving means a request should land in the cheapest/closest
healthy region, and when a region (or pool) fails, re-land within the tier's
SLO rather than dropping. Policy expresses the order; health is injected.

A region is `active` (eligible as a primary) or a `fallback` (used only when
no active region is healthy). Among healthy candidates we keep the policy's
preference order, and we never return a region whose estimated latency blows
the SLO when a within-SLO option exists.
"""

from dataclasses import dataclass


class NoRegionAvailable(Exception):
    pass


@dataclass
class RegionChoice:
    region: str
    failed_over: bool      # True if the preferred active region was unhealthy
    within_slo: bool


def choose_region(request_region, policy, *, is_region_healthy,
                  latency_ms_of=None, slo_ms=None) -> RegionChoice:
    """policy: {active: [regions...], fallback: [regions...], home: {region: pref}}.

    Preference order: the request's home region first (if active), then the
    rest of `active` in order, then `fallback` in order. The first healthy
    region that meets the SLO wins; if none meet it, the first healthy region
    wins (degraded but serving)."""
    active = list(policy.get("active", []))
    fallback = list(policy.get("fallback", []))

    ordered = []
    if request_region and request_region in active:
        ordered.append(request_region)
    ordered += [r for r in active if r not in ordered]
    ordered += [r for r in fallback if r not in ordered]

    healthy = [r for r in ordered if is_region_healthy(r)]
    if not healthy:
        raise NoRegionAvailable("no healthy region")

    preferred_active = next((r for r in active if is_region_healthy(r)), None)

    def within(r):
        if slo_ms is None or latency_ms_of is None:
            return True
        lat = latency_ms_of(r)
        return lat is None or lat <= slo_ms

    chosen = next((r for r in healthy if within(r)), healthy[0])
    failed_over = chosen != (request_region if request_region in active
                             else preferred_active)
    return RegionChoice(region=chosen, failed_over=failed_over,
                        within_slo=within(chosen))
