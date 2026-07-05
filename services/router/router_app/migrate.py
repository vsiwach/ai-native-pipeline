"""One-click certified migration — the console's "Run migration" button.

Server-side orchestration of the run the console's steps expose manually,
so the outcome doesn't depend on human choreography (or on the browser tab
staying open):

    wake pool -> adopt as candidate (cohort resets) -> voice traffic fills
    the cohort -> bench at the voice gate -> certify -> on PASS, PROMOTE:
    traffic moves from the frontier incumbent to the open-model GPU pool.

Composition, not reimplementation: each stage drives the router's OWN
localhost surface (the same endpoints the buttons hit), so gating, events,
ledger and evidence behave identically. Runs in a daemon thread; the
console polls GET /v1/dev/migrate for stage + detail. One run at a time.
Promotion happens ONLY on a PROMOTE_ELIGIBLE certificate — an automated
run cannot skip the gate, it can only fail it.
"""
from __future__ import annotations

import os
import threading
import time

import httpx

STAGES = ("wake_pool", "adopt", "traffic", "bench", "certify", "promote",
          "done")


class MigrationRun:
    def __init__(self, route: str = "voice-agent",
                 base: str | None = None, token: str = "",
                 traffic_s: float = 120.0, rps: float = 2.0):
        self.route = route
        self.base = (base or os.environ.get("LOADGEN_TARGET")
                     or "http://127.0.0.1:8114").rstrip("/")
        self.token = token
        self.traffic_s = float(traffic_s)
        self.rps = float(rps)
        self.stage = "starting"
        self.detail = ""
        self.error: str | None = None
        self.verdict: str | None = None
        self.started_at = time.time()
        self.finished = False
        self._thread: threading.Thread | None = None

    # -- plumbing ------------------------------------------------------------
    def _headers(self) -> dict:
        return {"X-Dev-Token": self.token} if self.token else {}

    def _get(self, path: str) -> dict:
        return httpx.get(f"{self.base}{path}", headers=self._headers(),
                         timeout=60).json()

    def _post(self, path: str, body: dict) -> dict:
        r = httpx.post(f"{self.base}{path}", json=body,
                       headers=self._headers(), timeout=60)
        out = r.json()
        if isinstance(out, dict) and out.get("error"):
            raise RuntimeError(out["error"].get("message", str(out)[:160]))
        return out

    def _set(self, stage: str, detail: str = "") -> None:
        self.stage, self.detail = stage, detail

    def _wait(self, predicate, timeout_s: float, interval_s: float = 10.0,
              what: str = "") -> bool:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                if predicate():
                    return True
            except Exception as exc:  # noqa: BLE001 — transient probe misses
                self.detail = f"{what}: {str(exc)[:80]}"
            time.sleep(interval_s)
        return False

    # -- lifecycle -----------------------------------------------------------
    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True,
                                        name="migration-run")
        self._thread.start()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def status(self) -> dict:
        return {"running": self.running, "stage": self.stage,
                "detail": self.detail, "error": self.error,
                "verdict": self.verdict, "route": self.route,
                "elapsed_s": round(time.time() - self.started_at, 1),
                "finished": self.finished}

    # -- the pipeline ----------------------------------------------------------
    def _pool(self) -> dict | None:
        pods = self._get("/v1/dev/gpu").get("pods", [])
        return next((p for p in pods if p["kind"] == "modal"), None) \
            or (pods[0] if pods else None)

    def _job_done(self, name: str) -> dict | None:
        j = self._get("/v1/dev/gpu").get("jobs", {}).get(name)
        return j if j and not j["running"] else None

    def _run(self) -> None:
        try:
            self._set("wake_pool", "waking the GPU pool (scale-from-zero; "
                                   "first wake can take minutes)")
            if not self._wait(lambda: (self._pool() or {}).get("ready"),
                              timeout_s=900, what="wake"):
                raise RuntimeError("pool never became ready (15 min)")
            pod = self._pool()
            self._set("adopt", f"adopting {pod['id']} as the candidate "
                               "(evidence cohort resets)")
            self._post("/v1/dev/gpu", {"action": "adopt",
                                       "pod_id": pod["id"],
                                       "route": self.route})

            self._set("traffic", f"voice traffic: {self.rps} rps for "
                                 f"{self.traffic_s:.0f}s, mirroring to the "
                                 "candidate")
            self._post("/v1/dev/loadgen", {
                "action": "start", "route": self.route, "rps": self.rps,
                "duration_s": self.traffic_s, "stream_ratio": 0.5})
            if not self._wait(
                    lambda: self._get("/v1/dev/loadgen").get("finished"),
                    timeout_s=self.traffic_s + 120, what="traffic"):
                raise RuntimeError("traffic run never finished")

            self._set("bench", "benching at the voice gate "
                               "(p99 TTFT < 500 ms)")
            self._post("/v1/dev/gpu", {"action": "bench",
                                       "pod_id": pod["id"]})
            if not self._wait(lambda: self._job_done("bench"),
                              timeout_s=600, what="bench"):
                raise RuntimeError("bench never finished")
            if self._job_done("bench")["rc"] != 0:
                raise RuntimeError("bench failed — see job tail")

            self._set("certify", "scoring parity + SLO, signing the record")
            self._post("/v1/dev/gpu", {"action": "certify",
                                       "pool": pod["kind"],
                                       "route": self.route})
            if not self._wait(lambda: self._job_done("certify"),
                              timeout_s=300, what="certify"):
                raise RuntimeError("certify never finished")
            cert = self._get("/v1/certs/latest")
            self.verdict = cert.get("verdict")
            if self.verdict != "PROMOTE_ELIGIBLE":
                # the gate refused — an automated run does NOT get to shrug
                # that off; it ends here, honestly
                self._set("done", f"certificate {self.verdict or 'HOLD'} — "
                                  "gate refused, route stays on the "
                                  "incumbent")
                return

            self._set("promote", "certificate PASS — moving traffic from "
                                 "the frontier incumbent to the open-model "
                                 "GPU pool")
            self._post(f"/v1/routes/{self.route}/promote", {})
            self._set("done", "MIGRATED — the open-model pool serves; "
                              "rollback stays armed")
        except Exception as exc:  # noqa: BLE001 — surfaced, never silent
            self.error = str(exc)[:200]
            self._set("done", f"failed at {self.stage}: {self.error}")
        finally:
            self.finished = True
