"""Governed incident agent — detect → diagnose → resolve, hands-off.

The agent watches live telemetry (per-pool SLO breach rates, health) and
drives incidents through the IncidentStore so the devboard shows the whole
lifecycle with a measured MTTR. Its production allowlist is deliberately
small (the mockup's contract):

    quarantine (eject pool from rotation — traffic spills to healthy pools)
    probe      (direct request to the sick pool to verify recovery)
    reinstate  (lift quarantine after consecutive passing probes)
    resolve    (close the incident once service SLO is restored)

No scale/rollback actions until F2/F5 wire them; adding an action means
adding it HERE, visibly. Set INCIDENT_AGENT=0 to run manual-baseline drills
(agent off, humans on the runbook — that contrast is the MTTR story).

Split for testability: IncidentAgentLogic is pure and clock-injected
(unit-tested hard); the Runner owns threads and HTTP probes.
"""

import threading
from dataclasses import dataclass, field


@dataclass
class PoolSignal:
    """One pool's telemetry snapshot, assembled by the runner each tick."""
    pool_id: str
    url: str
    usable: bool            # health poller's view (incl. our own quarantine)
    healthz_ok: bool        # raw health, ignoring quarantine
    breach_rate: float      # SLO-breaching fraction of recent samples
    samples: int            # sample count behind breach_rate


@dataclass
class Case:
    """Agent state for one incident it is working."""
    incident_id: str
    pool_id: str
    kind: str                       # pool_down | slo_breach
    phase: str = "diagnose"         # diagnose -> resolve (store phases)
    quarantined: bool = False
    probes_passed: int = 0
    probes_failed: int = 0          # consecutive; resets on a pass
    escalated: bool = False
    next_probe_at: float = 0.0
    resolved_at: float | None = None


@dataclass
class AgentConfig:
    breach_rate_threshold: float = 0.5
    min_samples: int = 4
    probe_interval_s: float = 3.0
    probes_to_reinstate: int = 2
    cooldown_s: float = 30.0
    # single-token probe must answer within the voice TTFT SLO — a pool
    # carrying +600ms injected latency can never pass verification
    probe_slo_ms: float = 500.0
    # a fault the allowlist can't fix (probes keep failing) escalates to a
    # human ONCE, loudly — the agent keeps the quarantine and keeps probing
    escalate_after_failures: int = 5


class IncidentAgentLogic:
    """Pure decision core. step() consumes signals, returns effect dicts the
    runner executes: {op: open|act|quarantine|probe|reinstate|resolve, ...}"""

    def __init__(self, config: AgentConfig | None = None):
        self.config = config or AgentConfig()
        self.cases: dict[str, Case] = {}      # pool_id -> active case
        self.cooldown_until: dict[str, float] = {}

    def step(self, now: float, signals: list[PoolSignal],
             healthy_pools: int) -> list[dict]:
        effects: list[dict] = []
        for sig in signals:
            case = self.cases.get(sig.pool_id)
            if case is None:
                opened = self._maybe_open(now, sig, healthy_pools)
                # `healthy_pools` was a tick-start snapshot: a quarantine we
                # just issued reduces it NOW, so two pools breaching in the
                # same tick can never both be quarantined (that would take
                # the whole service down — the exact failure the last-pool
                # guard exists to prevent). Quarantining an already-unusable
                # pool removes no capacity, so it doesn't decrement.
                if sig.usable and any(e["op"] == "quarantine"
                                      for e in opened):
                    healthy_pools -= 1
                effects.extend(opened)
            else:
                effects.extend(self._work_case(now, case, sig))
        return effects

    # ---- detection ---------------------------------------------------------

    def _maybe_open(self, now, sig, healthy_pools) -> list[dict]:
        if now < self.cooldown_until.get(sig.pool_id, 0.0):
            return []
        cfg = self.config
        if not sig.healthz_ok:
            kind, title, detect = (
                "pool_down",
                f"{sig.pool_id} down — health probe failing, traffic spilled",
                f"health probe failed on {sig.pool_id}")
        elif (sig.samples >= cfg.min_samples
              and sig.breach_rate >= cfg.breach_rate_threshold):
            kind, title, detect = (
                "slo_breach",
                f"{sig.pool_id} breaching serving SLO — "
                f"{sig.breach_rate:.0%} of recent requests",
                f"detected SLO breach rate {sig.breach_rate:.0%} "
                f"over {sig.samples} requests on {sig.pool_id}")
        else:
            return []
        # The guard protects the pools that would be LEFT: a sick pool that
        # is already unusable (health-down) contributes nothing, so
        # quarantining it costs nothing — count the others only.
        others_usable = healthy_pools - (1 if sig.usable else 0)
        if others_usable < 1:
            # quarantining the last pool would take the service down — a
            # bigger problem than a breach. Open the incident, act cautious.
            title += " · last healthy pool, quarantine withheld"
        case = Case(incident_id="", pool_id=sig.pool_id, kind=kind)
        self.cases[sig.pool_id] = case
        effects = [
            {"op": "open", "pool_id": sig.pool_id, "title": title},
            {"op": "act", "pool_id": sig.pool_id, "action": detect,
             "phase": "diagnose"},
        ]
        if others_usable >= 1:
            case.quarantined = True
            case.phase = "resolve"
            effects.append({"op": "quarantine", "pool_id": sig.pool_id,
                            "url": sig.url})
            effects.append({"op": "act", "pool_id": sig.pool_id,
                            "action": f"quarantined {sig.pool_id}; "
                                      "traffic spills to healthy pools",
                            "phase": "resolve"})
        case.next_probe_at = now + self.config.probe_interval_s
        return effects

    # ---- recovery ----------------------------------------------------------

    def _work_case(self, now, case, sig) -> list[dict]:
        effects: list[dict] = []
        if case.kind == "pool_down":
            if sig.healthz_ok:
                effects.extend(self._reinstate_and_resolve(
                    now, case, sig, "health probe recovered"))
            elif not case.resolved_at and case.quarantined:
                # service is safe on the remaining pools; keep the case open
                # until health returns, nothing to do this tick
                pass
            return effects
        # slo_breach: probe the sick pool directly until it behaves. After
        # escalation the case is a human's; slow-poll so a stuck quarantine
        # doesn't hammer (and further rate-limit) the upstream for hours.
        if now >= case.next_probe_at:
            interval = self.config.probe_interval_s * (
                5 if case.escalated else 1)
            case.next_probe_at = now + interval
            effects.append({"op": "probe", "pool_id": case.pool_id,
                            "url": sig.url})
        return effects

    def record_probe(self, now: float, pool_id: str, ok: bool,
                     latency_ms: float) -> list[dict]:
        case = self.cases.get(pool_id)
        if case is None:
            return []
        effects = [{"op": "act", "pool_id": pool_id,
                    "action": f"probe {'passed' if ok else 'failed'} "
                              f"({latency_ms:.0f}ms)",
                    "phase": "resolve"}]
        if ok:
            case.probes_passed += 1
            case.probes_failed = 0
            if case.probes_passed >= self.config.probes_to_reinstate:
                effects.extend(self._reinstate_and_resolve(
                    now, case, None,
                    f"{case.probes_passed} consecutive probes within SLO"))
        else:
            case.probes_passed = 0
            case.probes_failed += 1
            if (case.probes_failed >= self.config.escalate_after_failures
                    and not case.escalated):
                # nothing in the allowlist fixes this fault — page a human,
                # once, and keep the quarantine + probe loop running
                case.escalated = True
                effects.append({"op": "escalate", "pool_id": pool_id})
                effects.append({"op": "act", "pool_id": pool_id,
                                "action": f"escalating to on-call — "
                                          f"{case.probes_failed} consecutive "
                                          "probes failed; quarantine held, "
                                          "beyond agent allowlist",
                                "phase": "resolve"})
        return effects

    def _reinstate_and_resolve(self, now, case, sig, why) -> list[dict]:
        effects = []
        if case.quarantined:
            effects.append({"op": "reinstate", "pool_id": case.pool_id})
            effects.append({"op": "act", "pool_id": case.pool_id,
                            "action": f"reinstated {case.pool_id} — {why}",
                            "phase": "resolve"})
        effects.append({"op": "resolve", "pool_id": case.pool_id})
        self.cases.pop(case.pool_id, None)
        self.cooldown_until[case.pool_id] = now + self.config.cooldown_s
        return effects


class IncidentAgentRunner:
    """Owns the thread + I/O; every decision comes from the pure logic."""

    def __init__(self, state, interval_s: float = 2.0,
                 config: AgentConfig | None = None):
        self.state = state
        self.interval_s = interval_s
        self.logic = IncidentAgentLogic(config)
        self._ids: dict[str, str] = {}     # pool_id -> incident id
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ---- signal assembly ---------------------------------------------------

    def signals(self, now: float) -> tuple[list[PoolSignal], int]:
        from router_app import config as cfg
        model = self.state.devboard_model()
        if model is None:
            return [], 0
        # verification probes are judged against the SLO of the tier the
        # watched model actually serves — a hosted-API pool on the standard
        # tier (TTFT 2000ms) can never pass a hard-coded 500ms voice probe,
        # which would leave every quarantine stuck forever
        tier = self.state.registry.get(model, {}).get("tier", "realtime")
        tier_rules = self.state.policy["tiers"].get(tier, {})
        self.logic.config.probe_slo_ms = float(
            tier_rules.get("ttft_ms") or 500.0)
        replicas = cfg.replicas_for(self.state.policy, model)
        samples = self.state.metrics.window(15.0, now=None)
        by_replica = {}
        for s in samples:
            by_replica.setdefault(s.replica, []).append(s)
        out = []
        for rep in replicas:
            st = self.state.poller.status_for(rep["url"])
            pool_samples = by_replica.get(rep["id"], [])
            breaches = sum(1 for s in pool_samples if not s.slo_met)
            out.append(PoolSignal(
                pool_id=rep["id"], url=rep["url"],
                usable=st.usable,
                healthz_ok=st.healthy is not False,
                breach_rate=breaches / len(pool_samples)
                if pool_samples else 0.0,
                samples=len(pool_samples)))
        healthy = sum(1 for s in out if s.usable)
        return out, healthy

    # ---- effect execution ---------------------------------------------------

    def execute(self, now: float, effects: list[dict]) -> None:
        import time as _t
        for e in effects:
            pool = e.get("pool_id", "")
            if e["op"] == "open":
                inc = self.state.incidents.open(e["title"], agent=True)
                self._ids[pool] = inc["id"]
                if self.logic.cases.get(pool):
                    self.logic.cases[pool].incident_id = inc["id"]
            elif e["op"] == "act":
                if pool in self._ids:
                    self.state.incidents.act(self._ids[pool], e["action"],
                                             phase=e.get("phase"))
            elif e["op"] == "quarantine":
                self.state.poller.status_for(e["url"]).quarantined = True
                self.state.events.emit("agent_action", action="quarantine",
                                       pool=pool)
            elif e["op"] == "reinstate":
                url = self._url_of(pool)
                if url:
                    self.state.poller.status_for(url).quarantined = False
                self.state.events.emit("agent_action", action="reinstate",
                                       pool=pool)
            elif e["op"] == "escalate":
                self.state.events.emit("agent_escalation", pool=pool,
                                       reason="probes failing beyond "
                                              "allowlist remedies")
            elif e["op"] == "probe":
                ok, ms = self.probe(e["url"])
                self.execute(now, self.logic.record_probe(now, pool, ok, ms))
            elif e["op"] == "resolve":
                if pool in self._ids:
                    self.state.incidents.resolve(
                        self._ids.pop(pool),
                        postmortem_url=f"/v1/incidents?focus={pool}")
            _t.sleep(0)  # yield between effects

    def _url_of(self, pool_id: str):
        from router_app import config as cfg
        model = self.state.devboard_model()
        if model is None:
            return None
        for rep in cfg.replicas_for(self.state.policy, model):
            if rep["id"] == pool_id:
                return rep["url"]
        return None

    def probe(self, url: str) -> tuple[bool, float]:
        """Direct 1-token STREAMING completion against the sick pool; pass =
        first token within the probe SLO. The SLO is defined on TTFT, so the
        probe measures TTFT — timing a full non-stream completion would
        punish decode + upstream variance the SLO never promised (live
        hosted APIs routinely finish 1-token completions slower than their
        TTFT, which left quarantines stuck forever)."""
        import time as _t
        import httpx
        # probe with the model the board watches — a multi-model pool (the
        # Model API mux) resolves it exactly; "probe" would hit its default
        model = self.state.devboard_model() or "probe"
        body = {"model": model, "max_tokens": 1, "stream": True,
                "messages": [{"role": "user", "content": "probe"}]}
        slo_ms = self.logic.config.probe_slo_ms
        start = _t.monotonic()
        try:
            with httpx.stream("POST", f"{url}/v1/chat/completions",
                              json=body, timeout=slo_ms / 1000) as resp:
                if resp.status_code != 200:
                    return False, (_t.monotonic() - start) * 1000
                for line in resp.iter_lines():
                    if line.startswith("data:"):
                        ms = (_t.monotonic() - start) * 1000
                        return ms <= slo_ms, ms
            return False, (_t.monotonic() - start) * 1000
        except httpx.HTTPError:
            return False, (_t.monotonic() - start) * 1000

    # ---- lifecycle -----------------------------------------------------------

    def tick(self) -> None:
        import time as _t
        now = _t.monotonic()
        signals, healthy = self.signals(now)
        self.execute(now, self.logic.step(now, signals, healthy))

    def start(self) -> None:
        if self._thread:
            return

        def loop():
            while not self._stop.wait(self.interval_s):
                try:
                    self.tick()
                except Exception as exc:  # noqa: BLE001 — agent must never
                    # die, but it must never fail SILENTLY either
                    self.state.events.emit("agent_error", error=repr(exc))

        self._thread = threading.Thread(target=loop, daemon=True,
                                        name="incident-agent")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
