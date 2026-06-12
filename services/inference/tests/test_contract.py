"""Contract test — asserts the three endpoints from
contracts/inference.openapi.yaml exist and return the documented shapes.
Any service behind the router must pass an equivalent of this."""

from inference_app.core import config


def test_healthz_shape(test_client) -> None:
    response = test_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_info_shape(test_client) -> None:
    response = test_client.get("/v1/info")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "model": "house-price-reg",
        "version": "1.0",
        "tier": "standard",
        "target": "cpu",
    }
    assert body["tier"] in ("realtime", "standard", "batch")
    assert body["target"] in ("cpu", "gpu")


def test_predict_shape(test_client) -> None:
    response = test_client.post(
        "/v1/predict",
        json={
            "median_income_in_block": 8.3252,
            "median_house_age_in_block": 41,
            "average_rooms": 6,
            "average_bedrooms": 1,
            "population_per_block": 322,
            "average_house_occupancy": 2,
            "block_latitude": 37.88,
            "block_longitude": -122.23,
        },
        headers={"token": str(config.API_KEY)},
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["median_house_value"], int)
    assert body["currency"] == "USD"


def test_predict_requires_auth(test_client) -> None:
    response = test_client.post("/v1/predict", json={})
    assert response.status_code in (400, 401)
