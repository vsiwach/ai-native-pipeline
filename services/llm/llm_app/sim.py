"""MaxLocalSim — the default backend. Emulates MAX's OpenAI-compatible surface
AND the economics that make LLM serving hard (prefill/decode split, KV/prefix
cache with TTL, cold-start penalty), with no GPU.

Deterministic: given a seed it produces the same tokens and the same plan, and
the clock is injected so timing is reproducible in tests.
"""

import random

from llm_app.adapter import BackendAdapter, ChatRequest, Generation
from llm_app.economics import (Economics, ReplicaState, commit_plan,
                               plan_request)

# A tiny fixed vocabulary — completions are deterministic given the seed. The
# point is realistic token *counts* and streaming, not language quality.
_VOCAB = (
    "the model serves tokens through a prefill and decode loop while the kv "
    "cache holds recent prefixes so repeated prompts skip recompute and cost "
    "less latency drops when a replica is already warm otherwise a cold start "
    "dominates the time to first token across regions and pools").split()


class MaxLocalSim(BackendAdapter):
    engine = "max"

    def __init__(self, name: str, target: str = "cpu",
                 economics: Economics | None = None, clock=None,
                 replica: ReplicaState | None = None):
        self.name = name
        self.target = target
        self.econ = economics or Economics()
        self._clock = clock or __import__("time").monotonic
        self.replica = replica or ReplicaState()

    def capabilities(self) -> set[str]:
        return {"chat"}

    def info(self) -> dict:
        base = super().info()
        base.update({
            "backend": "max-local-sim",
            "cold_start_s": self.econ.cold_start_s,
            "kv_ttl_s": self.econ.kv_ttl_s,
            "prefix_tokens": self.econ.prefix_tokens,
            "warm": self.replica.warm_at is not None,
        })
        return base

    def _completion_tokens(self, n: int, seed: int | None) -> list[str]:
        rng = random.Random(seed if seed is not None else 0)
        words = [rng.choice(_VOCAB) for _ in range(n)]
        # space-join, keep spaces attached so "".join(tokens) reads naturally
        return [(w if i == 0 else " " + w) for i, w in enumerate(words)]

    def generate(self, request: ChatRequest) -> Generation:
        now = self._clock()
        prompt = request.prompt_text()
        plan = plan_request(prompt, request.max_tokens, self.econ,
                            self.replica, now)
        commit_plan(prompt, self.econ, self.replica, now)
        tokens = self._completion_tokens(plan.completion_tokens, request.seed)
        return Generation(
            request_id=f"chatcmpl-sim-{abs(hash((prompt, request.seed))) % 10**12}",
            model=self.name, tokens=tokens, plan=plan)
