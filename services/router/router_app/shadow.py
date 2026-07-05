"""Shadow mirror — the first stage of certified migration (PRD F1.2).

While a route's primary backend serves the user, an async mirror sends the
same request to the candidate backend and appends the (request, primary,
candidate, timings) tuple to an on-disk JSONL shadow log. Zero user impact:
mirroring is fire-and-forget, capped by a concurrency semaphore, and any
candidate failure is recorded, never surfaced.

Wire-up (router main.py):
    shadow = ShadowMirror(route="docs-assist", candidate_url=..., log_dir=...)
    ...
    primary_resp = await proxy(primary, request)
    shadow.submit(request_payload, primary_resp)   # non-blocking
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path

import httpx


class ShadowMirror:
    def __init__(
        self,
        route: str,
        candidate_url: str,
        log_dir: str | Path = "shadow-logs",
        max_inflight: int = 8,
        timeout_s: float = 60.0,
        api_key: str = "",
    ):
        self.route = route
        self.candidate_url = candidate_url.rstrip("/")
        self.log_path = Path(log_dir) / f"{route}.shadow.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._sem = asyncio.Semaphore(max_inflight)
        self._client = httpx.AsyncClient(timeout=timeout_s)
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.submitted = 0
        self.completed = 0
        self.failed = 0

    def submit(self, request_payload: dict, primary_response: dict) -> None:
        """Fire-and-forget mirror. Never raises into the serving path."""
        self.submitted += 1
        asyncio.get_event_loop().create_task(
            self._mirror(dict(request_payload), primary_response)
        )

    async def _mirror(self, payload: dict, primary_response: dict) -> None:
        rec = {
            "id": uuid.uuid4().hex,
            "route": self.route,
            "ts": time.time(),
            "request": payload,
            "primary": {"content": _content(primary_response)},
        }
        payload.pop("stream", None)  # shadow compares full completions
        async with self._sem:
            t0 = time.perf_counter()
            try:
                r = await self._client.post(
                    f"{self.candidate_url}/chat/completions",
                    json=payload, headers=self._headers,
                )
                body = r.json()
                rec["candidate"] = {
                    "content": _content(body),
                    "status": r.status_code,
                    "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                    "usage": body.get("usage", {}),
                    "citations": r.headers.get("X-Citations"),
                }
                self.completed += 1
            except Exception as e:  # noqa: BLE001 — shadow must never break serving
                rec["candidate"] = {"error": str(e)}
                self.failed += 1
        with self.log_path.open("a") as f:
            f.write(json.dumps(rec) + "\n")

    def stats(self) -> dict:
        return {
            "route": self.route,
            "submitted": self.submitted,
            "completed": self.completed,
            "failed": self.failed,
            "log": str(self.log_path),
        }

    async def aclose(self) -> None:
        await self._client.aclose()


def _content(openai_response: dict) -> str:
    try:
        return openai_response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return ""
