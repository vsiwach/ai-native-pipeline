# Route layout per contracts/inference.openapi.yaml:
#   /healthz at the root (unversioned, unauthenticated)
#   /v1/info, /v1/predict under the versioned prefix
from fastapi import APIRouter

from inference_app.api.routes import health, info, prediction

root_router = APIRouter()
root_router.include_router(health.router, tags=["health"])

v1_router = APIRouter()
v1_router.include_router(info.router, tags=["info"])
v1_router.include_router(prediction.router, tags=["prediction"])
