# Vendored from eightBEC/fastapi-ml-skeleton (Apache-2.0); import paths only.
from inference_app.core import config
from inference_app.models.payload import HousePredictionPayload
from inference_app.models.prediction import HousePredictionResult
from inference_app.services.models import HousePriceModel


def test_prediction(test_client) -> None:
    model_path = config.DEFAULT_MODEL_PATH
    hpp = HousePredictionPayload.model_validate(
        {
            "median_income_in_block": 8.3252,
            "median_house_age_in_block": 41,
            "average_rooms": 6,
            "average_bedrooms": 1,
            "population_per_block": 322,
            "average_house_occupancy": 2,
            "block_latitude": 37.88,
            "block_longitude": -122.23,
        }
    )

    hpm = HousePriceModel(model_path)
    result = hpm.predict(hpp)
    assert isinstance(result, HousePredictionResult)
