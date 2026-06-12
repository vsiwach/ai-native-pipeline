# Adapted from upstream heartbeat.py to our contract: GET /healthz.
from fastapi import APIRouter

from inference_app.models.heartbeat import HealthResult

router = APIRouter()


@router.get("/healthz", response_model=HealthResult, name="healthz")
def get_healthz() -> HealthResult:
    return HealthResult(status="ok")
