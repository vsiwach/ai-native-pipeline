"""Cold-start-aware autoscaling — pure control logic over a replica lifecycle.

LLM replicas have brutal cold starts (load tens–hundreds of GB of weights) on
expensive GPUs, so *when* and *how many* replicas exist is the core economic
lever. This controller is I/O-free: it reads a Fleet (pure data) + a demand
signal and a clock, mutates the fleet through its lifecycle, and returns the
scaling decisions (which the caller streams to the event log).

Lifecycle:  cold ──start──▶ warming ──(cold_start_s)──▶ warm ──idle──▶ draining ──▶ (removed)

Behaviors:
  - scale-to-zero        no demand + idle past timeout → drain to `min_warm`
                         (which may be 0)
  - warm pool / pre-warm keep `min_warm` replicas warm so bursts skip cold start
  - burst headroom       target ~`target_pending_per_replica` in-flight each
  - predictive pre-warm  an injected `forecast(now)` can raise desired ahead of
                         a known burst (schedule / traffic signal)
"""

from dataclasses import dataclass, field

COLD, WARMING, WARM, DRAINING = "cold", "warming", "warm", "draining"


@dataclass
class Replica:
    id: str
    state: str = COLD
    since: float = 0.0          # clock when it entered `state`


@dataclass
class Fleet:
    replicas: list[Replica] = field(default_factory=list)
    _n: int = 0

    def count(self, *states) -> int:
        return sum(1 for r in self.replicas if r.state in states)

    def in_state(self, *states) -> list[Replica]:
        return [r for r in self.replicas if r.state in states]

    def add(self, now: float) -> Replica:
        self._n += 1
        r = Replica(id=f"replica-{self._n}", state=WARMING, since=now)
        self.replicas.append(r)
        return r


@dataclass
class AutoscaleConfig:
    cold_start_s: float = 8.0
    min_warm: int = 0                       # warm pool floor (0 = scale-to-zero)
    max_replicas: int = 3
    target_pending_per_replica: int = 4
    idle_timeout_s: float = 30.0


class AutoScaler:
    def __init__(self, config: AutoscaleConfig, fleet: Fleet | None = None,
                 forecast=None, emit=None):
        self.cfg = config
        self.fleet = fleet or Fleet()
        self._forecast = forecast or (lambda now: 0)
        self._emit = emit or (lambda *a, **k: None)
        self._last_activity = 0.0

    def desired_warm(self, pending: int, now: float) -> int:
        demand = pending + self._forecast(now)
        need = -(-demand // self.cfg.target_pending_per_replica)  # ceil div
        desired = max(self.cfg.min_warm, need)
        if demand > 0:
            desired = max(desired, 1)
        return min(desired, self.cfg.max_replicas)

    def warm_available(self) -> bool:
        return self.fleet.count(WARM) > 0

    def step(self, now: float, pending: int) -> list[dict]:
        decisions: list[dict] = []
        if pending > 0:
            self._last_activity = now

        # 1. promote replicas that have finished their cold start
        for r in self.fleet.in_state(WARMING):
            if now - r.since >= self.cfg.cold_start_s:
                r.state, r.since = WARM, now
                decisions.append(self._decision("promote", r, now,
                                                reason="cold_start_complete"))

        desired = self.desired_warm(pending, now)
        live = self.fleet.count(WARM, WARMING)

        # 2. scale up toward desired (note any cold start the warm pool avoided)
        if live < desired:
            for _ in range(desired - live):
                r = self.fleet.add(now)
                absorbed = self.warm_available()
                decisions.append(self._decision(
                    "start", r, now, reason="scale_up",
                    cold_start_avoided_ms=(self.cfg.cold_start_s * 1000
                                           if absorbed else 0.0)))

        # 3. scale down when idle and over desired
        idle = (now - self._last_activity) >= self.cfg.idle_timeout_s
        if pending == 0 and idle:
            warm = self.fleet.in_state(WARM)
            for r in warm[desired:]:           # keep `desired` (>= min_warm)
                r.state, r.since = DRAINING, now
                decisions.append(self._decision("drain", r, now,
                                                reason="idle"))

        # 4. remove fully drained replicas
        for r in self.fleet.in_state(DRAINING):
            r.state = "removed"
            decisions.append(self._decision("stop", r, now, reason="drained"))
        self.fleet.replicas = [r for r in self.fleet.replicas
                               if r.state != "removed"]
        return decisions

    def _decision(self, action: str, r: Replica, now: float, **fields) -> dict:
        event = {"action": action, "replica": r.id, "state": r.state,
                 "ts": now, **fields}
        self._emit("scale", **event)
        return event
