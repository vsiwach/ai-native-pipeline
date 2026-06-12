# Vendored from eightBEC/fastapi-ml-skeleton (Apache-2.0); heartbeat became
# the contract's /healthz.
def test_healthz(test_client) -> None:
    response = test_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_default_route(test_client) -> None:
    response = test_client.get("/")
    assert response.status_code == 404
