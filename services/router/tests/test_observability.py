"""Config-as-UX + route-where simulator endpoints (Phase 10).
These need no chat backend — they exercise placement state + the router API."""

PLACEMENT = {
    "compliance": {"sensitive_capacity_tags": ["sensitive"]},
    "capacity_preference": ["cheapest"],
    "pools": [
        {"id": "gcp-us", "region": "us-central1", "provider": "gcp-cloudrun-cpu",
         "cost_rank": 1, "tags": []},
        {"id": "gcp-hipaa", "region": "us-central1", "provider": "gcp-cloudrun-cpu",
         "cost_rank": 3, "tags": ["sensitive"], "compliance_regimes": ["hipaa"]},
    ],
}


def test_info_advertises_capabilities(router_client):
    caps = router_client.get("/v1/info").json()["capabilities"]
    assert {"chat", "kv_affinity", "autoscale", "placement", "release"} <= set(caps)


def test_config_as_ux_placement_write_then_route_where(router_client):
    # edit the placement policy via the API (the UI's write-back path)
    resp = router_client.post("/v1/policy/placement", json=PLACEMENT)
    assert resp.status_code == 200 and resp.json()["pools"] == 2
    assert router_client.get("/v1/policy/placement").json() == PLACEMENT

    # the "route where" simulator reflects the new policy on the next call
    hipaa = router_client.get("/v1/simulate/route?compliance=hipaa").json()
    ids = [p["id"] for p in hipaa["eligible_pools"]]
    assert ids == ["gcp-hipaa"]                 # compliance denied ordinary pool

    general = router_client.get("/v1/simulate/route").json()
    gids = [p["id"] for p in general["eligible_pools"]]
    assert "gcp-us" in gids


def test_config_change_emits_event(router_client):
    router_client.post("/v1/policy/placement", json=PLACEMENT)
    counts = router_client.get("/v1/events").json()["counts"]
    assert counts.get("config_change", 0) >= 1
