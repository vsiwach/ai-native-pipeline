"""Router — the single public entrypoint for inference.

Request flow for POST /v1/predict?model=M&tier=T:
  cache -> healthy candidates from registry+policy -> tier-policy pick ->
  proxy -> record latency/cost -> X-Cache / X-Backend / X-Est-Cost headers.
Batch tier requests are enqueued instead (see batch.py, /v1/batch routes).
Config hot-reloads on SIGHUP. No per-model logic anywhere in this package.
"""

import json
import os
import signal
import time
from pathlib import Path

import httpx
from fastapi import FastAPI, Query, Request, Response
from fastapi.responses import JSONResponse

from router_app import config as cfg
from router_app.batch import BatchQueue, BatchWorker
from router_app.cache import TTLCache, cache_key
from router_app.costs import CostLedger
from router_app.autoscaler import AutoScaler, AutoscaleConfig
from router_app.events import EventLog
from router_app.health import HealthPoller
from router_app.kvstate import KVState
from router_app.placement import eligible_pools
from router_app.policy import (NoHealthyBackend, UnknownModel, resolve_tier,
                               select, select_replica)

ROUTER_VERSION = "1.0"
FORWARDED_HEADERS = ("token",)


class RouterState:
    def __init__(self, registry_path: Path | None = None,
                 policy_path: Path | None = None):
        self.registry_path = registry_path
        self.policy_path = policy_path
        self.ledger = CostLedger()
        self.events = EventLog()
        self.reload()
        self.poller = HealthPoller(
            get_endpoints=lambda: self.policy["endpoints"],
            interval_s=float(os.environ.get("HEALTH_POLL_INTERVAL_S", "10")),
        )
        queue_dir = Path(os.environ.get("ROUTER_QUEUE_DIR",
                                        "/tmp/router-batch-queue"))
        self.queue = BatchQueue(queue_dir)
        concurrency = int(self.policy["tiers"].get("batch", {})
                          .get("concurrency", 2))
        self.worker = BatchWorker(self.queue, self.process_batch_job,
                                  concurrency=concurrency)

    def reload(self) -> None:
        self.registry = cfg.load_registry(self.registry_path)
        self.policy = cfg.load_policy(self.policy_path)
        cache_cfg = self.policy["cache"]
        self.cache = TTLCache(ttl_s=float(cache_cfg.get("ttl_s", 300)),
                              enabled=bool(cache_cfg.get("enabled", True)))
        # KV/prefix state shared across reloads would lose warmth; keep it if
        # present, else create with the configured TTL.
        ttl = float(cache_cfg.get("ttl_s", 300))
        if getattr(self, "kvstate", None) is None:
            self.kvstate = KVState(kv_ttl_s=ttl)
        else:
            self.kvstate.kv_ttl_s = ttl
        self.placement = cfg.load_placement()
        if getattr(self, "autoscalers", None) is None:
            self.autoscalers = {}  # model -> AutoScaler (created on first use)

    def _autoscaler(self, model: str) -> AutoScaler:
        if model not in self.autoscalers:
            entry = self.registry.get(model, {})
            scale_to_zero = str(entry.get("scale_to_zero", "true")) == "true"
            self.autoscalers[model] = AutoScaler(
                AutoscaleConfig(
                    cold_start_s=float(entry.get("cold_start_s", 8.0)),
                    min_warm=0 if scale_to_zero else 1,
                    max_replicas=int(entry.get("max_replicas", 3))),
                emit=lambda kind, **f: self.events.emit(kind, model=model, **f))
        return self.autoscalers[model]

    def proxy_chat(self, model: str, body: dict, headers: dict,
                   region: str | None = None, compliance: str | None = None):
        """Select a replica with placement + prefix affinity, forward the chat
        completion, record LLM economics, and return (httpx.Response,
        ReplicaChoice). Raises UnknownModel / NoHealthyBackend."""
        if model not in self.registry:
            raise UnknownModel(model)
        replicas = cfg.replicas_for(self.policy, model)
        if not replicas:
            raise NoHealthyBackend(model)
        prompt = "\n".join(m.get("content", "")
                           for m in body.get("messages", []))
        tier = self.registry[model].get("tier", "realtime")
        tier_rules = self.policy["tiers"].get(tier, {})
        affinity = self.policy.get("affinity", {})

        # Layer 1 — placement: which capacity pools may serve this request.
        # Replicas declare a `pool` only when placement is in use; otherwise the
        # filter is a no-op (back-compat with the single-pool local demo).
        placement_filter = None
        if self.placement.get("pools") and (region or compliance):
            allowed = {p["id"] for p in eligible_pools(
                {"region": region, "compliance": compliance}, self.placement)}
            self.events.emit("placement", model=model, region=region,
                             compliance=compliance, eligible_pools=sorted(allowed))
            placement_filter = lambda c: c.get("pool") is None or c["pool"] in allowed

        # autoscale signal: in-flight requests for this model right now
        pending = sum(self.kvstate.pending(r["id"]) for r in replicas) + 1
        self._autoscaler(model).step(time.monotonic(), pending)

        choice = select_replica(
            prompt, replicas, is_usable=lambda u: self.poller.status_for(u).usable,
            kvstate=self.kvstate, tier_rules=tier_rules,
            cost_of=lambda p: float(self.policy["cost_table"].get(p, 0.0)),
            affinity_cfg=affinity, capacity=int(affinity.get("capacity", 8)),
            latency_of=lambda u: self.poller.status_for(u).p50_ms,
            placement_filter=placement_filter)

        self.kvstate.inc_pending(choice.replica_id)
        try:
            fwd = {k: v for k, v in headers.items()
                   if k.lower() in FORWARDED_HEADERS}
            resp = httpx.post(f"{choice.url}/v1/chat/completions", json=body,
                              headers=fwd, timeout=120)
            ttft = float(resp.headers.get("X-TTFT-Ms", 0.0))
            tps = float(resp.headers.get("X-Tokens-Per-Sec", 0.0))
            cost = float(resp.headers.get("X-Est-Cost", 0.0))
            prompt_tokens = int(resp.headers.get("X-Prompt-Tokens", 0))
            completion_tokens = int(resp.headers.get("X-Completion-Tokens", 0))
            backend_hit = resp.headers.get("X-Cache") == "hit"
        finally:
            self.kvstate.dec_pending(choice.replica_id)
        # record what the replica now holds (warm + prefix cached)
        self.kvstate.record_prefix(choice.replica_id, choice.prefix)
        slo_ttft = tier_rules.get("ttft_ms")
        slo_met = slo_ttft is None or ttft <= slo_ttft
        self.ledger.record_llm(
            model, choice.provider, est_cost_usd=cost,
            cache_hit=choice.cache_hit or backend_hit, ttft_ms=ttft,
            tokens_per_sec=tps, prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens, slo_met=slo_met)
        self.events.emit("route", model=model, replica=choice.replica_id,
                         provider=choice.provider, cache_hit=choice.cache_hit,
                         reason=choice.reason, ttft_ms=ttft)
        if not slo_met:
            # feeds the devboard's self-serve incident management
            self.events.emit("slo_breach", model=model,
                             replica=choice.replica_id, ttft_ms=round(ttft, 1),
                             slo_ttft_ms=slo_ttft, tier=tier,
                             remediation="scale up / reroute / roll back")
        return resp, choice

    # ---- core proxy path (shared by live predict and batch worker) ----

    def call_backend(self, model: str, tier_param: str | None,
                     payload: dict, headers: dict) -> tuple[dict, "object"]:
        """Returns (response_json, Choice). Raises UnknownModel /
        NoHealthyBackend. Failing endpoints are marked unhealthy and the
        next candidate is tried."""
        attempts = len(self.policy["endpoints"].get(model, [])) or 1
        last_error: Exception | None = None
        for _ in range(attempts):
            choice = select(model, tier_param, self.registry, self.policy,
                            self.poller.status_for)
            tier_rules = self.policy["tiers"].get(choice.tier, {})
            max_ms = tier_rules.get("max_latency_ms")
            timeout_s = (max_ms / 1000) if max_ms else 30.0
            start = time.monotonic()
            try:
                resp = httpx.post(
                    f"{choice.url}/v1/predict", json=payload,
                    headers={k: v for k, v in headers.items()
                             if k.lower() in FORWARDED_HEADERS},
                    timeout=timeout_s,
                )
                latency_ms = (time.monotonic() - start) * 1000
            except httpx.HTTPError as exc:
                self.poller.mark_unhealthy(choice.url)
                last_error = exc
                continue
            self.poller.record_latency(choice.url, latency_ms)
            if resp.status_code >= 500:
                self.poller.mark_unhealthy(choice.url)
                last_error = NoHealthyBackend(f"{choice.url} -> {resp.status_code}")
                continue
            self.ledger.record(model, choice.provider, choice.est_cost_usd,
                               latency_ms)
            body = resp.json() if resp.status_code == 200 else {
                "status_code": resp.status_code, "detail": resp.json()}
            if resp.status_code != 200:
                # backend rejected the request (auth/validation) — not a
                # routing failure; surface as-is without caching
                raise BackendRejection(resp.status_code, body["detail"])
            return body, choice
        raise NoHealthyBackend(str(last_error) if last_error else model)

    def process_batch_job(self, job: dict) -> dict:
        body, choice = self.call_backend(job["model"], "batch",
                                         job["payload"], job["headers"])
        return {"prediction": body, "backend": choice.provider,
                "est_cost_usd": choice.est_cost_usd}


class BackendRejection(Exception):
    def __init__(self, status_code: int, detail):
        self.status_code = status_code
        self.detail = detail


def _error(status: int, code: str, message: str, **extra) -> JSONResponse:
    return JSONResponse(status_code=status,
                        content={"error": {"code": code, "message": message,
                                           **extra}})


def get_app(registry_path: Path | None = None,
            policy_path: Path | None = None,
            start_background: bool = True) -> FastAPI:
    state = RouterState(registry_path, policy_path)
    app = FastAPI(title="inference-router", version=ROUTER_VERSION)
    app.state.router_state = state

    if start_background:
        state.poller.start()
        state.worker.start()
        try:  # SIGHUP hot-reload (unavailable in some test harnesses)
            signal.signal(signal.SIGHUP, lambda *_: state.reload())
        except ValueError:
            pass

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "degraded": state.poller.degraded()}

    @app.get("/v1/info")
    def info():
        return {"model": "router", "version": ROUTER_VERSION,
                "tier": "realtime", "target": "cpu",
                "capabilities": ["predict", "chat", "kv_affinity", "autoscale",
                                 "placement", "failover", "release",
                                 "costs", "events"]}

    @app.post("/v1/predict")
    async def predict(request: Request,
                      model: str = Query(...),
                      tier: str | None = Query(default=None)):
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            return _error(400, "invalid_json", "request body must be JSON")
        headers = dict(request.headers)

        try:
            resolved = resolve_tier(model, tier, state.registry, state.policy)
            tier_rules = state.policy["tiers"].get(resolved, {})
        except UnknownModel:
            return _error(404, "unknown_model",
                          f"model '{model}' is not in inference-registry.yaml",
                          model=model)

        if tier_rules.get("queue"):
            job_id = state.queue.submit(model, payload, {
                k: v for k, v in headers.items()
                if k.lower() in FORWARDED_HEADERS})
            return JSONResponse(status_code=202, content={
                "job_id": job_id, "status": "pending",
                "poll": f"/v1/batch/{job_id}"})

        key = cache_key(model, payload)
        cached = state.cache.get(key)
        if cached is not None:
            entry = json.loads(cached)
            state.ledger.record(model, entry["provider"], 0.0, cached=True)
            return JSONResponse(content=entry["body"], headers={
                "X-Cache": "hit", "X-Backend": entry["provider"],
                "X-Est-Cost": "0"})

        try:
            body, choice = state.call_backend(model, tier, payload, headers)
        except UnknownModel:
            return _error(404, "unknown_model",
                          f"model '{model}' is not in inference-registry.yaml",
                          model=model)
        except NoHealthyBackend as exc:
            return _error(503, "no_healthy_backend",
                          f"no healthy backend for model '{model}': {exc}",
                          model=model)
        except BackendRejection as exc:
            return JSONResponse(status_code=exc.status_code,
                                content=exc.detail if isinstance(exc.detail, dict)
                                else {"detail": exc.detail})

        state.cache.put(key, json.dumps(
            {"body": body, "provider": choice.provider}).encode())
        return JSONResponse(content=body, headers={
            "X-Cache": "miss", "X-Backend": choice.provider,
            "X-Est-Cost": f"{choice.est_cost_usd:.10f}"})

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request,
                               model: str = Query(default=None),
                               region: str = Query(default=None),
                               compliance: str = Query(default=None)):
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return _error(400, "invalid_json", "request body must be JSON")
        model = model or body.get("model")
        try:
            resp, choice = state.proxy_chat(model, body, dict(request.headers),
                                            region=region, compliance=compliance)
        except UnknownModel:
            return _error(404, "unknown_model",
                          f"model '{model}' is not in inference-registry.yaml",
                          model=model)
        except NoHealthyBackend as exc:
            return _error(503, "no_healthy_backend",
                          f"no healthy replica for model '{model}': {exc}",
                          model=model)
        except httpx.HTTPError as exc:
            return _error(502, "backend_error", f"chat backend failed: {exc}",
                          model=model)
        headers = {
            "X-Backend": choice.provider, "X-Replica": choice.replica_id,
            "X-Cache": "hit" if choice.cache_hit else "miss",
            "X-Route-Reason": choice.reason,
        }
        media = resp.headers.get("content-type", "application/json")
        if media.startswith("text/event-stream"):
            return Response(content=resp.content, media_type=media,
                            headers=headers)
        return JSONResponse(content=resp.json(), headers=headers)

    @app.get("/v1/events")
    def events(limit: int = 100, kind: str | None = None):
        return {"events": state.events.recent(limit, kind),
                "counts": state.events.kinds()}

    # ---- config-as-UX: the policy stays the source of truth; the devboard is
    # a lens that can read it and propose changes that take effect live. ----
    @app.get("/v1/policy/placement")
    def get_placement():
        return state.placement

    @app.post("/v1/policy/placement")
    async def set_placement(request: Request):
        new_policy = await request.json()
        state.placement = new_policy            # applies to the next request
        state.events.emit("config_change", target="placement-policy",
                          pools=[p.get("id") for p in new_policy.get("pools", [])])
        return {"status": "applied", "pools": len(new_policy.get("pools", []))}

    @app.get("/v1/simulate/route")
    def simulate_route(region: str | None = None, compliance: str | None = None):
        """'What would route where' — eligible capacity for a hypothetical
        request under the CURRENT placement policy, without sending traffic."""
        from router_app.placement import eligible_pools
        pools = eligible_pools({"region": region, "compliance": compliance},
                               state.placement)
        return {"region": region, "compliance": compliance,
                "eligible_pools": [{"id": p["id"], "region": p.get("region"),
                                    "sensitive": "sensitive" in p.get("tags", [])}
                                   for p in pools]}

    @app.post("/v1/batch")
    async def submit_batch(request: Request, model: str = Query(...)):
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            return _error(400, "invalid_json", "request body must be JSON")
        if model not in state.registry:
            return _error(404, "unknown_model",
                          f"model '{model}' is not in inference-registry.yaml",
                          model=model)
        headers = {k: v for k, v in request.headers.items()
                   if k.lower() in FORWARDED_HEADERS}
        job_id = state.queue.submit(model, payload, headers)
        return JSONResponse(status_code=202, content={
            "job_id": job_id, "status": "pending",
            "poll": f"/v1/batch/{job_id}"})

    @app.get("/v1/batch/{job_id}")
    def batch_status(job_id: str):
        job = state.queue.get(job_id)
        if job is None:
            return _error(404, "unknown_job", f"no job '{job_id}'")
        return {"job_id": job["id"], "status": job["status"],
                "result": job["result"], "error": job["error"]}

    @app.get("/v1/costs")
    def costs():
        snap = state.ledger.snapshot()
        snap["cache"] = {"hits": state.cache.hits,
                         "misses": state.cache.misses,
                         "hit_rate": round(state.cache.hit_rate, 4)}
        return snap

    return app


app = get_app() if os.environ.get("ROUTER_AUTOSTART", "1") == "1" else None
