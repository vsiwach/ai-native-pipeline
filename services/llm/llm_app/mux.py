"""ModelAPIMux — one pool proxy that serves EVERY model in a hosted catalog.

Baseten's Model APIs are one multi-tenant endpoint serving many models, so the
natural pool shape is one proxy that dispatches per-request on `model` instead
of one proxy process per model. The mux owns a catalog of sub-adapters (one
per catalog entry) and routes each ChatRequest to the right one; the HTTP
layer and the router need zero changes — the mux is just a BackendAdapter
whose models() lists the whole catalog.

The catalog is deploy/baseten/model-apis.json, GENERATED from the live
/v1/models listing by `deploy/baseten/manage.py catalog` (provenance: every
alias, slug and price traces to that GET). Adding a model to the platform =
refreshing the catalog. No code changes, no GPU sizing, no SKU roulette.

Keyless / offline (the repo's no-GPU-no-keys rule): without
BASETEN_API_BASE_URL the mux builds a per-model MaxLocalSim carrying that
model's real per-token prices, so routing, economics, chaos drills and the
devboard exercise the same multi-model surface with zero network.
"""

import json
import os
from pathlib import Path

from llm_app.adapter import BackendAdapter, ChatRequest, Generation


class ModelAPIMux(BackendAdapter):
    """Dispatch ChatRequests across a catalog of sub-adapters by model name.

    Resolution order: exact alias -> upstream slug -> default alias. Falling
    back to the default keeps single-purpose probes (the incident agent's
    1-token verification) working without knowing the catalog."""

    engine = "baseten-api"
    target = "gpu"

    def __init__(self, name: str, adapters: dict[str, BackendAdapter],
                 default_alias: str, catalog_meta: dict | None = None):
        if not adapters:
            raise ValueError("ModelAPIMux needs at least one catalog adapter")
        if default_alias not in adapters:
            raise ValueError(f"default alias {default_alias!r} not in catalog")
        self.name = name
        self._adapters = adapters
        self._by_slug = {getattr(a, "model_id", alias): alias
                         for alias, a in adapters.items()}
        self.default_alias = default_alias
        self.catalog_meta = catalog_meta or {}

    def resolve(self, model: str | None) -> BackendAdapter:
        if model in self._adapters:
            return self._adapters[model]
        if model in self._by_slug:
            return self._adapters[self._by_slug[model]]
        return self._adapters[self.default_alias]

    # ---- BackendAdapter ----------------------------------------------------

    def capabilities(self) -> set[str]:
        return {"chat"}

    def models(self) -> list[str]:
        return sorted(self._adapters)

    def info(self) -> dict:
        base = super().info()
        default = self._adapters[self.default_alias]
        base.update({
            "backend": getattr(default, "backend_label",
                               type(default).__name__),
            "served_models": self.models(),
            "default_model": self.default_alias,
            "catalog_source": self.catalog_meta.get("source"),
            "catalog_fetched_at": self.catalog_meta.get("fetched_at"),
        })
        return base

    def healthz(self) -> dict:
        # One upstream serves the whole catalog, so the default adapter's
        # health IS the mux's health.
        return self._adapters[self.default_alias].healthz()

    def generate(self, request: ChatRequest) -> Generation:
        return self.resolve(request.model).generate(request)

    def stream_raw(self, request: ChatRequest):
        sub = self.resolve(request.model)
        if hasattr(sub, "stream_raw"):
            yield from sub.stream_raw(request)
            return
        # sim sub-adapters have no raw stream; the HTTP layer paces
        # generate() output instead — mirror that shape here
        from llm_app.serialize import sse_stream
        yield from sse_stream(sub.generate(request))


def load_catalog(path: str | None = None) -> dict:
    """Load model-apis.json. Search order: MODEL_API_CATALOG env / argument,
    the repo checkout, the container image root (/srv)."""
    candidates = [p for p in (
        path,
        os.environ.get("MODEL_API_CATALOG"),
        str(Path(__file__).resolve().parents[3]
            / "deploy" / "baseten" / "model-apis.json"),
        "/srv/model-apis.json",
    ) if p]
    for cand in candidates:
        p = Path(cand)
        if p.exists():
            return json.loads(p.read_text())
    raise FileNotFoundError(
        "model-apis.json not found — generate it with "
        "`python3 deploy/baseten/manage.py catalog` or set MODEL_API_CATALOG")


def build_model_api_mux(name: str, base_url: str | None = None,
                        catalog_path: str | None = None,
                        default_alias: str | None = None) -> ModelAPIMux:
    """Build the mux from the catalog: live adapters when base_url is set
    (BASETEN_API_BASE_URL, key required), per-model sims otherwise."""
    catalog = load_catalog(catalog_path)
    entries = catalog.get("models", [])
    if not entries:
        raise ValueError("model-apis.json has no models")
    adapters: dict[str, BackendAdapter] = {}
    for m in entries:
        alias = m["alias"]
        if base_url:
            from llm_app.openai_compat import BasetenModelAPIAdapter
            adapters[alias] = BasetenModelAPIAdapter(
                alias, base_url=base_url, model_id=m["slug"],
                usd_per_1m_prompt=m.get("usd_per_1m_prompt"),
                usd_per_1m_completion=m.get("usd_per_1m_completion"))
        else:
            from llm_app.economics import Economics
            from llm_app.sim import MaxLocalSim
            sim = MaxLocalSim(alias, target="gpu", economics=Economics(
                # hosted API shape: always-warm multi-tenant fleet, so the
                # cold-start penalty is negligible; prices are the model's
                # real per-token prices from the catalog snapshot
                cold_start_s=float(os.environ.get("COLD_START_S", "0.5")),
                kv_ttl_s=float(os.environ.get("KV_TTL_S", "300.0")),
                decode_ms_per_token=float(
                    os.environ.get("DECODE_MS_PER_TOKEN", "20.0")),
                usd_per_1m_prompt_tokens=m.get("usd_per_1m_prompt", 0.0),
                usd_per_1m_completion_tokens=m.get(
                    "usd_per_1m_completion", 0.0)))
            sim.engine = "baseten-api"  # honest identity: API pool, sim backend
            sim.model_id = m["slug"]    # slug dispatch works keyless too
            adapters[alias] = sim
    if not default_alias:   # None or "" (an unset env var passed through)
        default_alias = os.environ.get("MODEL_API_DEFAULT") or min(
            entries, key=lambda m: m.get("usd_per_1m_completion", 0.0))["alias"]
    return ModelAPIMux(name, adapters, default_alias,
                       catalog_meta={k: catalog.get(k)
                                     for k in ("source", "fetched_at",
                                               "base_url")})
