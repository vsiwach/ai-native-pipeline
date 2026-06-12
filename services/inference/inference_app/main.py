# Vendored from eightBEC/fastapi-ml-skeleton (Apache-2.0); adapted to the
# repo inference contract (healthz at root, API under /v1).
from fastapi import FastAPI

from inference_app.api.routes.router import root_router, v1_router
from inference_app.core.config import APP_NAME, IS_DEBUG, MODEL_VERSION
from inference_app.core.event_handlers import start_app_handler, stop_app_handler


def get_app() -> FastAPI:
    fast_app = FastAPI(title=APP_NAME, version=MODEL_VERSION, debug=IS_DEBUG)
    fast_app.include_router(root_router)
    fast_app.include_router(v1_router, prefix="/v1")

    fast_app.add_event_handler("startup", start_app_handler(fast_app))
    fast_app.add_event_handler("shutdown", stop_app_handler(fast_app))

    return fast_app


app = get_app()
