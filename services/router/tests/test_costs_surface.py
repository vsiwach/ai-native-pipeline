"""/v1/costs Phase 6 extensions: measured per-pool economics repeated from
tools/bench.py reports (never estimated) and per-route serving/shadowed
counters — the exact shape vercel-deploy/demo.html polls. Additive: the
pre-existing snapshot fields must survive."""

import json

from tests.test_release_routes import BODY, migration_client  # noqa: F401


def test_costs_exposes_routes_and_bench_pools(migration_client, tmp_path):  # noqa: F811
    c = migration_client
    reports = tmp_path / "bench-reports"
    reports.mkdir()
    (reports / "a100.json").write_text(json.dumps({
        "kind": "modular-demo/bench-report", "pool": "a100",
        "usd_per_mtok": 0.31, "p99_ttft_ms": 412.0, "p99_tpot_ms": 21.0,
        "pool_usd_hr": 1.64, "measured_at": "2026-07-05T00:00:00Z"}))
    # newer report for the same pool wins; junk and foreign json are skipped
    (reports / "a100-rerun.json").write_text(json.dumps({
        "kind": "modular-demo/bench-report", "pool": "a100",
        "usd_per_mtok": 0.29, "p99_ttft_ms": 398.0, "p99_tpot_ms": 20.0,
        "pool_usd_hr": 1.64, "measured_at": "2026-07-05T01:00:00Z"}))
    (reports / "junk.json").write_text("not json")
    (reports / "other.json").write_text(json.dumps({"kind": "unrelated"}))

    c.post("/v1/chat/completions?model=docs-assist", json=BODY)
    c.state.shadows["docs-assist"].flush(timeout_s=5)
    d = c.get("/v1/costs").json()
    assert d["routes"]["docs-assist"] == {"serving": "frontier",
                                          "shadowed": 1}
    assert d["pools"] == [{"id": "a100", "usd_per_mtok": 0.29,
                           "p99_ttft_ms": 398.0, "p99_tpot_ms": 20.0,
                           "pool_usd_hr": 1.64,
                           "measured_at": "2026-07-05T01:00:00Z"}]
    # pre-existing snapshot fields survive (additive change)
    assert "backends" in d and "cache" in d


def test_costs_pools_empty_without_reports(migration_client):  # noqa: F811
    d = migration_client.get("/v1/costs").json()
    assert d["pools"] == []
    assert d["routes"]["docs-assist"]["serving"] == "frontier"
    assert d["routes"]["docs-assist"]["shadowed"] == 0
