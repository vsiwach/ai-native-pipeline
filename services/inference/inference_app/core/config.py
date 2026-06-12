# Vendored from eightBEC/fastapi-ml-skeleton (Apache-2.0); adapted:
# API key comes from INFERENCE_API_KEY, model path defaults to the bundled
# sample model, and the service declares its registry identity here.
from pathlib import Path

from starlette.config import Config
from starlette.datastructures import Secret

MODEL_NAME = "house-price-reg"
MODEL_VERSION = "1.0"
COST_TIER = "standard"
COMPUTE_TARGET = "cpu"

APP_NAME = "House Price Prediction Example"

_SAMPLE_MODEL = (
    Path(__file__).resolve().parents[2] / "sample_model"
    / "lin_reg_california_housing_model.joblib"
)

config = Config(".env")

API_KEY: Secret = config("INFERENCE_API_KEY", cast=Secret)
IS_DEBUG: bool = config("IS_DEBUG", cast=bool, default=False)

DEFAULT_MODEL_PATH: str = config("DEFAULT_MODEL_PATH", default=str(_SAMPLE_MODEL))
