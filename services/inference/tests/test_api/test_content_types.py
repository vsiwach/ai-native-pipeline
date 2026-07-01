# Contract hygiene: every endpoint must speak JSON, and the unauthenticated
# surface (/healthz, /v1/info) must stay reachable without a token.


def test_healthz_is_json_and_unauthenticated(test_client) -> None:
    response = test_client.get("/healthz")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_info_is_json_and_unauthenticated(test_client) -> None:
    response = test_client.get("/v1/info")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_auth_errors_are_json(test_client) -> None:
    response = test_client.post("/v1/predict", json={})
    assert response.headers["content-type"].startswith("application/json")
