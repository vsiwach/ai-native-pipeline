# Vendored from eightBEC/fastapi-ml-skeleton (Apache-2.0); adapted env vars
# (INFERENCE_API_KEY) and a path-independent model location so the suite runs
# from any cwd (plain pytest, Bazel runfiles, CI).
from pathlib import Path

import pytest
from starlette.config import environ
from starlette.testclient import TestClient

_SERVICE_DIR = Path(__file__).resolve().parent.parent

environ["INFERENCE_API_KEY"] = "a1279d26-63ac-41f1-8266-4ef3702ad7cb"
environ["DEFAULT_MODEL_PATH"] = str(
    _SERVICE_DIR / "sample_model" / "lin_reg_california_housing_model.joblib"
)

from inference_app.main import get_app  # noqa: E402


@pytest.fixture()
def test_client():
    app = get_app()
    with TestClient(app) as test_client:
        yield test_client
