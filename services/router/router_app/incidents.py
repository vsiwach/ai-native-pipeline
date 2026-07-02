"""IncidentStore — the incident timeline behind GET /v1/incidents.

Incidents are opened by real triggers (health ejection, SLO-breach streaks,
chaos drills) and driven through detect → diagnose → resolve with an action
log. agent=False rows are manual-runbook baseline drills; the MTTR story
(hero card, history chart) derives from this store. Thread-safe, clock
injected, no I/O.
"""

import threading


class IncidentStore:
    def __init__(self, clock=None, emit=None, max_incidents: int = 200):
        import time
        self._clock = clock or time.time
        self._emit = emit or (lambda kind, **f: None)
        self._max = max_incidents
        self._lock = threading.Lock()
        self._incidents: list[dict] = []
        self._seq = 0

    def open(self, title: str, agent: bool = True) -> dict:
        with self._lock:
            self._seq += 1
            inc = {
                "id": f"INC-{self._seq:04d}",
                "title": title,
                "ts": self._clock(),
                "phase_ms": {"detect": 0.0, "diagnose": 0.0, "resolve": 0.0},
                "mttr_s": 0.0,
                "agent": agent,
                "actions": [],
                "postmortem_url": None,
                "live": True,
                "_opened": self._clock(),
                "_phase_started": self._clock(),
                "_phase": "detect",
            }
            self._incidents.append(inc)
            if len(self._incidents) > self._max:
                self._incidents = self._incidents[-self._max:]
        self._emit("incident_open", id=inc["id"], title=title, agent=agent)
        return inc

    def _find(self, incident_id: str) -> dict | None:
        for inc in self._incidents:
            if inc["id"] == incident_id:
                return inc
        return None

    def act(self, incident_id: str, action: str,
            phase: str | None = None) -> dict | None:
        """Append an action; optionally advance the phase (detect → diagnose
        → resolve), closing out the elapsed time of the current phase."""
        with self._lock:
            inc = self._find(incident_id)
            if inc is None or not inc["live"]:
                return None
            now = self._clock()
            inc["actions"].append(action)
            if phase and phase != inc["_phase"]:
                elapsed_ms = (now - inc["_phase_started"]) * 1000.0
                inc["phase_ms"][inc["_phase"]] += round(elapsed_ms, 1)
                inc["_phase"] = phase
                inc["_phase_started"] = now
        self._emit("incident_action", id=incident_id, action=action,
                   phase=phase)
        return inc

    def resolve(self, incident_id: str,
                postmortem_url: str | None = None) -> dict | None:
        with self._lock:
            inc = self._find(incident_id)
            if inc is None or not inc["live"]:
                return None
            now = self._clock()
            elapsed_ms = (now - inc["_phase_started"]) * 1000.0
            inc["phase_ms"][inc["_phase"]] += round(elapsed_ms, 1)
            inc["mttr_s"] = round(now - inc["_opened"], 1)
            inc["live"] = False
            inc["postmortem_url"] = postmortem_url
        self._emit("incident_resolved", id=incident_id,
                   mttr_s=inc["mttr_s"])
        return inc

    def snapshot(self) -> list[dict]:
        """Public shape (contract order: newest first), private keys dropped;
        live incidents report elapsed time so MTTR badges can count up."""
        with self._lock:
            out = []
            now = self._clock()
            for inc in reversed(self._incidents):
                pub = {k: v for k, v in inc.items() if not k.startswith("_")}
                if inc["live"]:
                    pub["mttr_s"] = round(now - inc["_opened"], 1)
                    pub["phase_ms"] = dict(inc["phase_ms"])
                    pub["phase_ms"][inc["_phase"]] += round(
                        (now - inc["_phase_started"]) * 1000.0, 1)
                out.append(pub)
            return out

    def mttr_median(self, agent: bool) -> float:
        vals = sorted(i["mttr_s"] for i in self._incidents
                      if not i["live"] and i["agent"] == agent)
        if not vals:
            return 0.0
        mid = len(vals) // 2
        return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2
