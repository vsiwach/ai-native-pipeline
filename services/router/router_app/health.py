"""Background health poller: marks endpoints healthy/unhealthy and keeps a
rolling latency window per endpoint (p50 feeds lowest_latency routing)."""

import statistics
import threading
import time
from collections import deque

import httpx


class EndpointHealth:
    def __init__(self, window: int = 20):
        self.healthy: bool | None = None  # None = never polled (optimistic)
        self.latencies_ms: deque[float] = deque(maxlen=window)
        self.last_progress: float | None = None  # last token-progress clock
        self.ejected: bool = False                # stuck → ejected, recoverable
        # Incident-agent quarantine: STICKY — a successful health poll does
        # NOT clear it (a latency-poisoned pool answers /healthz fine); only
        # the agent lifts it after verification probes pass.
        self.quarantined: bool = False

    @property
    def usable(self) -> bool:
        return self.healthy is not False and not self.ejected \
            and not self.quarantined

    @property
    def p50_ms(self) -> float | None:
        if not self.latencies_ms:
            return None
        return statistics.median(self.latencies_ms)

    def stuck(self, now: float, deadline_s: float) -> bool:
        """A replica generating tokens that stops making progress within the
        deadline is stuck (hung mid-generation) even if /healthz still answers."""
        if self.last_progress is None:
            return False
        return (now - self.last_progress) > deadline_s


class HealthPoller:
    def __init__(self, get_endpoints, interval_s: float = 10.0,
                 timeout_s: float = 2.0):
        """get_endpoints: () -> {model: [{provider, url}, ...]} (live view,
        so SIGHUP config reloads are picked up automatically)."""
        self._get_endpoints = get_endpoints
        self.interval_s = interval_s
        self.timeout_s = timeout_s
        self._status: dict[str, EndpointHealth] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def status_for(self, url: str) -> EndpointHealth:
        with self._lock:
            if url not in self._status:
                self._status[url] = EndpointHealth()
            return self._status[url]

    def mark_unhealthy(self, url: str) -> None:
        self.status_for(url).healthy = False

    def record_latency(self, url: str, ms: float) -> None:
        status = self.status_for(url)
        status.latencies_ms.append(ms)
        status.healthy = True

    def record_progress(self, url: str, now: float) -> None:
        """Note token progress (called as a replica streams) so stuck
        detection can tell a slow generation from a hung one."""
        self.status_for(url).last_progress = now

    def detect_stuck(self, now: float, deadline_s: float) -> list[str]:
        """Eject replicas hung mid-generation. Returns the ejected urls.
        Recovery is automatic: a later successful health poll clears it."""
        ejected = []
        with self._lock:
            items = list(self._status.items())
        for url, status in items:
            if status.usable and status.stuck(now, deadline_s):
                status.ejected = True
                ejected.append(url)
        return ejected

    def poll_once(self) -> None:
        urls = {ep["url"]
                for eps in self._get_endpoints().values() for ep in eps}
        for url in urls:
            status = self.status_for(url)
            start = time.monotonic()
            try:
                resp = httpx.get(f"{url}/healthz", timeout=self.timeout_s)
                ok = resp.status_code == 200
            except httpx.HTTPError:
                ok = False
            if ok:
                status.latencies_ms.append((time.monotonic() - start) * 1000)
                if status.ejected:  # a stuck replica that answers again recovers
                    status.ejected = False
                    status.last_progress = None
            status.healthy = ok

    def degraded(self) -> bool:
        with self._lock:
            return any(s.healthy is False or s.ejected or s.quarantined
                       for s in self._status.values())

    def start(self) -> None:
        if self._thread:
            return

        def loop():
            while not self._stop.wait(self.interval_s):
                self.poll_once()

        self._thread = threading.Thread(target=loop, daemon=True,
                                        name="health-poller")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
