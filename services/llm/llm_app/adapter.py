"""The one interface every serving backend implements, so the router (and this
service's HTTP layer) treat them uniformly. Selection is config-driven via the
manifest's `engine` + `target` — never hard-coded.

Three implementations ship:
  - MaxLocalSim   (sim.py)        default, no GPU, faithful economics
  - MaxContainer  (container.py)  proxies a real `max serve`, target: gpu only
  - SklearnPredict(sklearn_adapter.py) wraps the legacy /v1/predict backend

Adapters advertise `capabilities()` ({"chat"} and/or {"predict"}); the HTTP
layer only mounts the routes an adapter supports.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable

from llm_app.economics import Plan


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatRequest:
    model: str
    messages: list[ChatMessage]
    max_tokens: int = 64
    stream: bool = False
    seed: int | None = None

    def prompt_text(self) -> str:
        """Flatten messages to the text the economics model prices."""
        return "\n".join(f"{m.role}: {m.content}" for m in self.messages)

    @classmethod
    def from_dict(cls, body: dict) -> "ChatRequest":
        return cls(
            model=body.get("model", "default"),
            messages=[ChatMessage(m.get("role", "user"), m.get("content", ""))
                      for m in body.get("messages", [])],
            max_tokens=int(body.get("max_tokens", 64)),
            stream=bool(body.get("stream", False)),
            seed=body.get("seed"),
        )


@dataclass
class Generation:
    """A fully-computed completion. The economics (plan) are decided up front
    and deterministically; the HTTP layer either returns the whole thing or
    paces `tokens` out as SSE. Keeping compute separate from pacing is what
    makes the sim unit-testable without real time."""

    request_id: str
    model: str
    tokens: list[str]
    plan: Plan = field(repr=False)

    @property
    def text(self) -> str:
        return "".join(self.tokens)

    def usage(self) -> dict:
        return {"prompt_tokens": self.plan.prompt_tokens,
                "completion_tokens": self.plan.completion_tokens,
                "total_tokens": self.plan.prompt_tokens
                + self.plan.completion_tokens}


class BackendAdapter(ABC):
    """Uniform backend surface. name/engine/target identify it in /v1/info."""

    name: str = "backend"
    engine: str = "max"
    target: str = "cpu"

    @abstractmethod
    def capabilities(self) -> set[str]:
        """Subset of {"chat", "predict"} this backend serves."""

    def healthz(self) -> dict:
        return {"status": "ok"}

    def info(self) -> dict:
        return {"model": self.name, "engine": self.engine,
                "target": self.target,
                "capabilities": sorted(self.capabilities())}

    def models(self) -> list[str]:
        return [self.name]

    def generate(self, request: ChatRequest) -> Generation:
        raise NotImplementedError(f"{type(self).__name__} does not serve chat")

    def predict(self, payload: dict) -> dict:
        raise NotImplementedError(
            f"{type(self).__name__} does not serve predict")


def join_stream(tokens: Iterable[str]) -> str:
    return "".join(tokens)
