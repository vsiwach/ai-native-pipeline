"""The economics of LLM serving, modeled faithfully enough to make the hard
problems visible — prefill vs decode, a KV/prefix cache with a TTL, and
cold-start penalties — without needing a GPU.

Everything here is PURE and INJECTABLE: no wall-clock, no real sleeps. The
caller passes a monotonic `clock` (seconds) so unit tests are deterministic and
the live server can pass `time.monotonic`. This is the same I/O-free discipline
as the router's policy engine.
"""

import hashlib
from dataclasses import dataclass, field


def estimate_tokens(text: str) -> int:
    """Rough token count — 1 token ≈ 4 chars, min 1. Deterministic, good
    enough for relative prefill/decode economics."""
    return max(1, len(text) // 4)


def prefix_hash(text: str, prefix_tokens: int) -> str:
    """Hash of the first `prefix_tokens` worth of text — the KV cache key.
    Two prompts sharing a prefix collide here, which is the whole point."""
    prefix_chars = prefix_tokens * 4
    return hashlib.sha256(text[:prefix_chars].encode()).hexdigest()[:16]


@dataclass
class Economics:
    """Per-replica cost/latency model. All times in milliseconds unless noted.

    Defaults are illustrative GPU-ish numbers; every service overrides them from
    its service.py manifest (cold_start_s, kv_ttl_s) and routing policy.
    """

    prefill_ms_per_token: float = 0.4
    decode_ms_per_token: float = 6.0
    cold_start_s: float = 8.0
    kv_ttl_s: float = 300.0
    prefix_tokens: int = 32
    # $/1M tokens — prefill (input) priced below decode (output), like real APIs
    usd_per_1m_prompt_tokens: float = 0.30
    usd_per_1m_completion_tokens: float = 1.20
    # a prefix-cache hit replays KV instead of recomputing prefill: ~10% the cost
    cache_read_fraction: float = 0.10
    # writing a new prefix into the KV cache adds ~25% over a plain prefill
    cache_write_multiplier: float = 1.25


@dataclass
class ReplicaState:
    """Mutable per-replica view the simulator threads through requests.
    `warm_at` is the clock time the replica finished its cold start (None =
    never started / cold). `kv_cache` maps prefix_hash -> expiry clock time."""

    warm_at: float | None = None
    kv_cache: dict[str, float] = field(default_factory=dict)


@dataclass
class Plan:
    """The computed cost of serving one request — what the sim will 'spend'."""

    prompt_tokens: int
    completion_tokens: int
    cold_start_ms: float
    prefill_ms: float
    decode_ms: float
    cache_hit: bool
    est_cost_usd: float

    @property
    def ttft_ms(self) -> float:
        """Time to first token = cold start + prefill (decode starts after)."""
        return self.cold_start_ms + self.prefill_ms

    @property
    def total_ms(self) -> float:
        return self.cold_start_ms + self.prefill_ms + self.decode_ms

    @property
    def tokens_per_sec(self) -> float:
        return (self.completion_tokens / (self.decode_ms / 1000)
                if self.decode_ms > 0 else 0.0)


def plan_request(prompt: str, max_tokens: int, econ: Economics,
                 replica: ReplicaState, now: float) -> Plan:
    """Compute the cost of serving `prompt` on `replica` at clock time `now`.

    Pure: does not mutate `replica`. Apply the result with `commit_plan` so the
    cold start / cache write are recorded exactly once (after the model decides
    to actually run this replica)."""
    prompt_tokens = estimate_tokens(prompt)
    completion_tokens = max(1, max_tokens)

    cold = replica.warm_at is None
    cold_start_ms = econ.cold_start_s * 1000 if cold else 0.0

    key = prefix_hash(prompt, econ.prefix_tokens)
    expiry = replica.kv_cache.get(key)
    cache_hit = expiry is not None and expiry > now

    full_prefill = prompt_tokens * econ.prefill_ms_per_token
    if cache_hit:
        prefill_ms = full_prefill * econ.cache_read_fraction
    else:
        prefill_ms = full_prefill * econ.cache_write_multiplier

    decode_ms = completion_tokens * econ.decode_ms_per_token

    cost = (prompt_tokens / 1_000_000 * econ.usd_per_1m_prompt_tokens
            + completion_tokens / 1_000_000 * econ.usd_per_1m_completion_tokens)
    if cache_hit:  # skipped prefill compute is the cache's dollar saving
        cost -= (prompt_tokens / 1_000_000 * econ.usd_per_1m_prompt_tokens
                 * (1 - econ.cache_read_fraction))

    return Plan(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
                cold_start_ms=cold_start_ms, prefill_ms=prefill_ms,
                decode_ms=decode_ms, cache_hit=cache_hit,
                est_cost_usd=round(cost, 10))


def commit_plan(prompt: str, econ: Economics, replica: ReplicaState,
                now: float) -> None:
    """Record the side effects of serving: the replica is now warm, and its
    prefix is in the KV cache with a fresh TTL."""
    if replica.warm_at is None:
        replica.warm_at = now + econ.cold_start_s
    key = prefix_hash(prompt, econ.prefix_tokens)
    replica.kv_cache[key] = now + econ.kv_ttl_s
