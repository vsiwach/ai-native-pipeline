"""End-to-end router behavior against a stdlib mock backend: cache headers,
failover to 503 envelope, degraded healthz, cost accounting."""

PAYLOAD = {"median_income_in_block": 8.3252, "average_rooms": 6}


def test_healthz_ok_not_degraded(router_client):
    router_client.state.poller.poll_once()
    resp = router_client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "degraded": False}


def test_info_contract(router_client):
    body = router_client.get("/v1/info").json()
    assert body["model"] == "router"
    assert body["tier"] in ("realtime", "standard", "batch")
    assert body["target"] in ("cpu", "gpu")


def test_predict_miss_then_hit(router_client):
    first = router_client.post("/v1/predict?model=house-price-reg",
                               json=PAYLOAD)
    assert first.status_code == 200
    assert first.headers["x-cache"] == "miss"
    assert first.headers["x-backend"] == "local-docker"
    assert float(first.headers["x-est-cost"]) > 0

    second = router_client.post("/v1/predict?model=house-price-reg",
                                json=PAYLOAD)
    assert second.status_code == 200
    assert second.headers["x-cache"] == "hit"
    assert second.json() == first.json()


def test_different_payload_is_cache_miss(router_client):
    router_client.post("/v1/predict?model=house-price-reg", json=PAYLOAD)
    other = router_client.post("/v1/predict?model=house-price-reg",
                               json={**PAYLOAD, "average_rooms": 7})
    assert other.headers["x-cache"] == "miss"


def test_unknown_model_404_envelope(router_client):
    resp = router_client.post("/v1/predict?model=ghost", json=PAYLOAD)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "unknown_model"


def test_dead_backend_503_envelope_and_degraded_healthz(router_client):
    router_client.handler.healthy = False
    router_client.state.poller.poll_once()

    resp = router_client.post("/v1/predict?model=house-price-reg",
                              json={"fresh": "payload"})
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "no_healthy_backend"
    assert body["error"]["model"] == "house-price-reg"

    health = router_client.get("/healthz")
    assert health.status_code == 200
    assert health.json() == {"status": "ok", "degraded": True}


def test_cached_responses_survive_dead_backend(router_client):
    router_client.post("/v1/predict?model=house-price-reg", json=PAYLOAD)
    router_client.handler.healthy = False
    router_client.state.poller.poll_once()
    resp = router_client.post("/v1/predict?model=house-price-reg",
                              json=PAYLOAD)
    assert resp.status_code == 200
    assert resp.headers["x-cache"] == "hit"


def test_costs_accumulate(router_client):
    router_client.post("/v1/predict?model=house-price-reg", json=PAYLOAD)
    router_client.post("/v1/predict?model=house-price-reg", json=PAYLOAD)
    snap = router_client.get("/v1/costs").json()
    backend = snap["backends"]["house-price-reg@local-docker"]
    assert backend["requests"] == 1
    assert backend["cache_hits"] == 1
    assert backend["cache_hit_rate"] == 0.5
    assert snap["total_est_cost_usd"] > 0
    assert snap["cache"]["hits"] == 1


def test_hot_reload_picks_up_policy_change(router_client, tmp_path):
    state = router_client.state
    assert state.cache.ttl_s == 300.0
    new_policy = state.policy_path.read_text().replace("ttl_s: 300",
                                                       "ttl_s: 7")
    state.policy_path.write_text(new_policy)
    state.reload()  # what the SIGHUP handler calls
    assert state.cache.ttl_s == 7.0
