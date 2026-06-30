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

    # default everywhere else: the no-GPU simulator
    econ = Economics(
        cold_start_s=float(os.environ.get("COLD_START_S", "8.0")),
        kv_ttl_s=float(os.environ.get("KV_TTL_S", "300.0")),
    )
    return MaxLocalSim(name, target=target, economics=econ)
