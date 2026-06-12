# Contract endpoint: GET /v1/info — identity, version, and registry tier/target.
from fastapi import APIRouter

from inference_app.core.config import (
    COMPUTE_TARGET,
    COST_TIER,
    MODEL_NAME,
    MODEL_VERSION,
)
from inference_app.models.info import InfoResult

router = APIRouter()


@router.get("/info", response_model=InfoResult, name="info")
def get_info() -> InfoResult:
    return InfoResult(
        model=MODEL_NAME,
        version=MODEL_VERSION,
        tier=COST_TIER,
        target=COMPUTE_TARGET,
    )
