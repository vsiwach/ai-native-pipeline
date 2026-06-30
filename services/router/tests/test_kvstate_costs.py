"""KV state (cache holds + pending load) and the LLM cost-ledger metrics."""

from router_app.costs import CostLedger
from router_app.events import EventLog
from router_app.kvstate import KVState


def test_kv_holds_with_ttl_expiry():
    clock = [0.0]
    kv = KVState(kv_ttl_s=100.0, clock=lambda: clock[0])
    assert kv.holds("r0", "p1") is False
    kv.record_prefix("r0", "p1")
    assert kv.holds("r0", "p1") is True
    clock[0] = 101.0
    assert kv.holds("r0", "p1") is False


def test_pending_inc_dec_never_negative():
    kv = KVState()
    kv.inc_pending("r0")
    kv.inc_pending("r0")
    kv.dec_pending("r0")
    assert kv.pending("r0") == 1
    kv.dec_pending("r0")
    kv.dec_pending("r0")  # underflow guarded
    assert kv.pending("r0") == 0


def test_ledger_reports_llm_metrics():
    ledger = CostLedger()
    ledger.record_llm("llm-sim", "local-docker", est_cost_usd=0.002,
                      cache_hit=False, ttft_ms=120.0, tokens_per_sec=80.0,
                      prompt_tokens=100, completion_tokens=50)
    ledger.record_llm("llm-sim", "local-docker", est_cost_usd=0.001,
                      cache_hit=True, ttft_ms=20.0, tokens_per_sec=90.0,
                      prompt_tokens=100, completion_tokens=50)
    snap = ledger.snapshot()
    b = snap["backends"]["llm-sim@local-docker"]
    assert b["requests"] == 2
    assert b["cache_hits"] == 1
    assert b["cache_hit_rate"] == 0.5
    assert b["avg_ttft_ms"] == 70.0          # (120 + 20) / 2
    assert b["avg_tokens_per_sec"] == 85.0
    assert b["completion_tokens"] == 100
    assert b["usd_per_1m_tokens"] is not None  # $/1M tokens computed
    assert b["goodput"] == 1.0                 # both met SLO (default)


def test_ledger_goodput_tracks_slo_breaches():
    ledger = CostLedger()
    ledger.record_llm("llm-sim", "p", est_cost_usd=0.0, cache_hit=False,
                      ttft_ms=100.0, tokens_per_sec=80.0, prompt_tokens=10,
                      completion_tokens=10, slo_met=True)
    ledger.record_llm("llm-sim", "p", est_cost_usd=0.0, cache_hit=False,
                      ttft_ms=9000.0, tokens_per_sec=80.0, prompt_tokens=10,
                      completion_tokens=10, slo_met=False)
    b = ledger.snapshot()["backends"]["llm-sim@p"]
    assert b["goodput"] == 0.5                 # 1 of 2 met SLO


def test_predict_backend_has_null_llm_fields():
    ledger = CostLedger()
    ledger.record("house-price-reg", "local-docker", 4e-7, latency_ms=12.0)
    b = ledger.snapshot()["backends"]["house-price-reg@local-docker"]
    assert b["avg_ttft_ms"] is None
    assert b["avg_latency_ms"] == 12.0


def test_event_log_records_and_filters():
    log = EventLog(clock=lambda: 1.0)
    log.emit("route", model="llm-sim", replica="r0")
    log.emit("scale", replica="r1")
    assert len(log.recent()) == 2
    assert len(log.recent(kind="route")) == 1
    assert log.kinds() == {"route": 1, "scale": 1}
