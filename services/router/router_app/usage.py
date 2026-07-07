"""Usage log for the BYOC-MVP demo — the answer to 'did someone run it?'

Records the two meaningful events (a migration was started; a route was
promoted) with a timestamp and best-effort client identity. Backed by a
`modal.Dict` when the router runs on Modal, so the record SURVIVES the
serverless container scaling to zero and restarting; degrades to an
in-process ring buffer otherwise. Every path is wrapped so usage logging
can never break the router.
"""
from __future__ import annotations

import time
from collections import deque

import os

_MEM: deque[dict] = deque(maxlen=200)
_DICT_NAME = "byoc-mvp-usage"


def _dict():
    # only the DEPLOYED router (router_stack.py sets USAGE_DURABLE=1) writes
    # to the shared workspace Dict — otherwise local test runs, which use the
    # same authenticated modal client, would pollute the production log
    if os.environ.get("USAGE_DURABLE") != "1":
        return None
    try:
        import modal
        return modal.Dict.from_name(_DICT_NAME, create_if_missing=True)
    except Exception:  # noqa: BLE001 — not on Modal, or client unavailable
        return None


def record(kind: str, **fields) -> None:
    """kind: 'migration_start' | 'promote' | 'rollback'."""
    ev = {"ts": time.time(), "kind": kind, **fields}
    _MEM.append(ev)
    d = _dict()
    if d is not None:
        try:
            log = d.get("log", [])
            log.append(ev)
            d["log"] = log[-500:]
        except Exception:  # noqa: BLE001 — durability is best-effort
            pass


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def summary() -> dict:
    events = None
    d = _dict()
    if d is not None:
        try:
            events = d.get("log", [])
        except Exception:  # noqa: BLE001
            events = None
    if events is None:
        events = list(_MEM)
    runs = [e for e in events if e["kind"] == "migration_start"]
    promotes = [e for e in events if e["kind"] == "promote"]
    return {
        "total_runs": len(runs),
        "total_promotes": len(promotes),
        "last_run": _iso(runs[-1]["ts"]) if runs else None,
        "distinct_clients": len({e.get("ip") for e in runs if e.get("ip")}),
        "durable": d is not None,
        "recent": [{**e, "at": _iso(e["ts"])} for e in events[-25:]],
    }
