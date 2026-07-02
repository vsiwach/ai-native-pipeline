"""Build the configured BackendAdapter from environment — which the manifest's
registry entry supplies (engine, target, cold_start_s, kv_ttl_s, model_id).
This is the only place adapter selection happens; the HTTP layer is adapter-
agnostic. Swapping engine/target needs ZERO router or app code change.
"""

import os

from llm_app.adapter import BackendAdapter
from llm_app.economics import Economics
from llm_app.sim import MaxLocalSim


def build_adapter() -> BackendAdapter:
    engine = os.environ.get("ENGINE", "max")
    target = os.environ.get("TARGET", "cpu")
    name = os.environ.get("MODEL_NAME", "llm-sim")

    if engine == "sklearn":
        from sklearn_adapter import SklearnPredict
        return SklearnPredict(
            name, base_url=os.environ.get("SKLEARN_BASE_URL",
                                          "http://inference:8080"))

    if engine == "max" and target == "gpu" and os.environ.get("MAX_BASE_URL"):
        from container import MaxContainer
        return MaxContainer(name, base_url=os.environ["MAX_BASE_URL"],
                            model_id=os.environ.get("MODEL_ID"))

    if engine == "baseten-api":
        # Baseten hosted Model APIs: one mux pool serves the whole catalog.
        # Live when BASETEN_API_BASE_URL is set (key required, same *_BASE_URL
        # gate as the other pools — tests and keyless dev get per-model sims
        # carrying the catalog's real per-token prices).
        from llm_app.mux import build_model_api_mux
        return build_model_api_mux(
            name, base_url=os.environ.get("BASETEN_API_BASE_URL"),
            catalog_path=os.environ.get("MODEL_API_CATALOG"),
            default_alias=os.environ.get("MODEL_API_DEFAULT"))

    if engine in ("baseten", "vllm"):
        # Live pool when its base URL is configured; otherwise the same
        # surface via the local sim with pool-tuned economics, so the whole
        # platform runs and tests with no keys, GPU, or network.
        url_env = "BASETEN_BASE_URL" if engine == "baseten" else "VLLM_BASE_URL"
        base_url = os.environ.get(url_env)
        if base_url:
            from llm_app.openai_compat import BasetenAdapter, VllmAdapter
            cls = BasetenAdapter if engine == "baseten" else VllmAdapter
            adapter = cls(name, base_url=base_url,
                          model_id=os.environ.get("MODEL_ID"),
                          usd_per_hour=float(
                              os.environ.get("POOL_USD_PER_HOUR", "0")))
            # Baseten serves two invocation styles: Engine-Builder is
            # OpenAI-compatible (/v1/chat/completions, the class default);
            # a custom Truss model.py is invoked at /predict. Config, not
            # code: BASETEN_CHAT_PATH=/predict flips per instance.
            if engine == "baseten" and os.environ.get("BASETEN_CHAT_PATH"):
                adapter.chat_path = os.environ["BASETEN_CHAT_PATH"]
            return adapter
        econ = Economics(
            cold_start_s=float(os.environ.get("COLD_START_S", "8.0")),
            kv_ttl_s=float(os.environ.get("KV_TTL_S", "300.0")),
            prefill_ms_per_token=float(
                os.environ.get("PREFILL_MS_PER_TOKEN", "0.4")),
            decode_ms_per_token=float(
                os.environ.get("DECODE_MS_PER_TOKEN", "6.0")),
            usd_per_1m_completion_tokens=float(
                os.environ.get("USD_PER_1M_COMPLETION", "1.20")),
        )
        sim = MaxLocalSim(name, target=target, economics=econ)
        sim.engine = engine  # honest identity: pool engine, sim backend
        return sim

    # default everywhere else: the no-GPU simulator
    econ = Economics(
        cold_start_s=float(os.environ.get("COLD_START_S", "8.0")),
        kv_ttl_s=float(os.environ.get("KV_TTL_S", "300.0")),
    )
    return MaxLocalSim(name, target=target, economics=econ)
