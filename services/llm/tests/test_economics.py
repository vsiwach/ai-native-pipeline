"""The simulator's economics, tested deterministically: prefill/decode split,
KV/prefix cache hit + TTL, and the cold-start penalty."""

from llm_app.adapter import ChatMessage, ChatRequest
from llm_app.economics import (Economics, ReplicaState, commit_plan,
                               estimate_tokens, plan_request, prefix_hash)


def _req(text, max_tokens=16, seed=1):
    return ChatRequest("llm-sim", [ChatMessage("user", text)],
                       max_tokens=max_tokens, seed=seed)


def test_token_estimate_monotonic():
    assert estimate_tokens("a" * 40) > estimate_tokens("a" * 4)
    assert estimate_tokens("") == 1


def test_shared_prefix_collides_in_hash():
    a = "the quick brown fox jumps over the lazy dog and keeps going forever"
    b = "the quick brown fox jumps over the lazy dog but then stops abruptly"
    assert prefix_hash(a, 8) == prefix_hash(b, 8)


def test_cold_start_dominates_ttft_then_disappears(clock):
    econ = Economics(cold_start_s=8.0)
    replica = ReplicaState()
    cold = plan_request("hello world", 16, econ, replica, clock())
    assert cold.cold_start_ms == 8000.0
    assert cold.ttft_ms >= 8000.0

    commit_plan("hello world", econ, replica, clock())
    clock.advance(8.0)  # replica finished warming
    warm = plan_request("hello world", 16, econ, replica, clock())
    assert warm.cold_start_ms == 0.0
    assert warm.ttft_ms < cold.ttft_ms


def test_prefix_cache_hit_cuts_prefill_and_cost(clock):
    econ = Economics(cold_start_s=0.0, prefix_tokens=8)
    replica = ReplicaState()
    prompt = "the quick brown fox jumps over the lazy dog goes on and on here"

    miss = plan_request(prompt, 16, econ, replica, clock())
    assert miss.cache_hit is False
    commit_plan(prompt, econ, replica, clock())

    hit = plan_request(prompt, 16, econ, replica, clock())
    assert hit.cache_hit is True
    assert hit.prefill_ms < miss.prefill_ms
    assert hit.est_cost_usd < miss.est_cost_usd


def test_kv_cache_entry_expires_after_ttl(clock):
    econ = Economics(cold_start_s=0.0, kv_ttl_s=300.0, prefix_tokens=8)
    replica = ReplicaState()
    prompt = "shared prefix tokens that exceed the configured prefix length ok"
    plan_request(prompt, 8, econ, replica, clock())
    commit_plan(prompt, econ, replica, clock())

    assert plan_request(prompt, 8, econ, replica, clock()).cache_hit is True
    clock.advance(301.0)  # past TTL
    assert plan_request(prompt, 8, econ, replica, clock()).cache_hit is False


def test_decode_scales_with_output_tokens(clock):
    econ = Economics(cold_start_s=0.0)
    replica = ReplicaState()
    short = plan_request("hi", 4, econ, replica, clock())
    long = plan_request("hi", 64, econ, replica, clock())
    assert long.decode_ms > short.decode_ms
    assert long.tokens_per_sec > 0


def test_generation_is_deterministic_given_seed(sim):
    g1 = sim.generate(_req("explain caching", seed=7))
    # fresh replica to avoid warm/cache coupling in the comparison
    from llm_app.economics import Economics, ReplicaState
    from llm_app.sim import MaxLocalSim
    sim2 = MaxLocalSim("llm-sim", economics=Economics(),
                       clock=lambda: 0.0, replica=ReplicaState())
    g2 = sim2.generate(_req("explain caching", seed=7))
    assert g1.tokens == g2.tokens
