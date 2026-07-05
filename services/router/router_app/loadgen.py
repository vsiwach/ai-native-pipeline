"""In-router synthetic load driver — the dev surface behind the console's
"generate load" button (same family as /v1/dev/chaos).

The browser can't spawn tools/loadgen.py, so the router can drive an
open-loop workload against itself: seeded Poisson arrivals at a target RPS,
a stream/non-stream ratio, a concurrency cap, and a hard duration. Requests
go through the ordinary /v1/chat/completions path, so everything downstream
(shadow mirroring, metrics, ledger, events) behaves exactly as under real
traffic. tools/loadgen.py stays the CLI twin for scripted/benchmark runs
with per-request CSVs; this one answers a button.

Dev-only by nature: one run at a time, bounded duration, capped in-flight.
"""
from __future__ import annotations

import asyncio
import random
import time

import httpx

# EXACT copies of evals/docs_qa.jsonl questions (certify matches shadow
# records to eval items by question text, so console-driven load must ask
# the eval questions verbatim). Built-in because evals/ does not ship in
# the router container; keep in sync when the eval set changes.
DEFAULT_QUESTIONS = [
    "Under what open-source license are the MAX framework libraries and serving layer released?",
    "Which parts of Mojo are open source, and what did Modular open up beyond the source code?",
    "What is Mammoth in the Modular stack?",
    "Which hardware vendors does MAX support for serving on day 0?",
    "What is the role of the Mojo standard library and kernels — are they open source?",
    "How does KV-aware routing decide where a request lands?",
    "What is disaggregated serving and why does it lower cost?",
    "Can I self-host MAX for single-node serving for free?",
    "What skills does the Modular skills repo provide for coding agents?",
    "What Python interoperability does Mojo offer?",
    "Which open model families does Modular serve with day-0 coverage?",
    "What does the OpenAI-compatible endpoint on MAX expose?",
]
MAX_DURATION_S = 600.0
MAX_RPS = 20.0


class LoadRun:
    """One bounded load run. Counters are plain ints mutated on the event
    loop only; status() is safe to call from any request handler."""

    def __init__(self, target: str, route: str, rps: float = 2.0,
                 duration_s: float = 120.0, stream_ratio: float = 0.5,
                 seed: int = 42, max_inflight: int = 8,
                 questions: list[str] | None = None, emit=None):
        self.target = target.rstrip("/")
        self.route = route
        self.rps = min(float(rps), MAX_RPS)
        self.duration_s = min(float(duration_s), MAX_DURATION_S)
        self.stream_ratio = float(stream_ratio)
        self.seed = int(seed)
        self.questions = questions or DEFAULT_QUESTIONS
        self._sem = asyncio.Semaphore(max_inflight)
        self._emit = emit or (lambda kind, **f: None)
        self._task: asyncio.Task | None = None
        self.started_at = time.time()
        self.sent = 0
        self.ok = 0
        self.errors = 0
        self.finished = False
        self.last_error: str | None = None

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        self._task = asyncio.get_running_loop().create_task(self._run())

    def stop(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def status(self) -> dict:
        return {
            "running": self.running,
            "route": self.route,
            "rps": self.rps,
            "duration_s": self.duration_s,
            "stream_ratio": self.stream_ratio,
            "seed": self.seed,
            "elapsed_s": round(time.time() - self.started_at, 1),
            "sent": self.sent,
            "ok": self.ok,
            "errors": self.errors,
            "last_error": self.last_error,
            "finished": self.finished,
        }

    # -- the loop ----------------------------------------------------------
    async def _one(self, client: httpx.AsyncClient, question: str,
                   stream: bool) -> None:
        # temperature 0: certification cohorts should be reproducible —
        # same question, same context, same answer
        body = {"messages": [{"role": "user", "content": question}],
                "max_tokens": 120, "stream": stream, "temperature": 0}
        url = f"{self.target}/v1/chat/completions"
        async with self._sem:
            try:
                if stream:
                    async with client.stream(
                            "POST", url, params={"model": self.route},
                            json=body) as r:
                        async for _ in r.aiter_lines():
                            pass
                    status = r.status_code
                else:
                    status = (await client.post(
                        url, params={"model": self.route},
                        json=body)).status_code
                if status == 200:
                    self.ok += 1
                else:
                    self.errors += 1
            except Exception as exc:  # noqa: BLE001 — an error is a data point
                self.errors += 1
                self.last_error = str(exc)[:160] or type(exc).__name__

    async def _run(self) -> None:
        rng = random.Random(self.seed)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.duration_s
        self._emit("loadgen", action="start", route=self.route,
                   rps=self.rps, duration_s=self.duration_s)
        tasks: list[asyncio.Task] = []
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                while loop.time() < deadline:
                    wait = rng.expovariate(self.rps)
                    remaining = deadline - loop.time()
                    if wait >= remaining:
                        break
                    await asyncio.sleep(wait)
                    self.sent += 1
                    tasks.append(loop.create_task(self._one(
                        client, rng.choice(self.questions),
                        rng.random() < self.stream_ratio)))
                await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            for t in tasks:
                t.cancel()
            raise
        finally:
            self.finished = True
            self._emit("loadgen", action="done", route=self.route,
                       sent=self.sent, ok=self.ok, errors=self.errors)
