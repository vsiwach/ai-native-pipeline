import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_app.economics import Economics, ReplicaState  # noqa: E402
from llm_app.sim import MaxLocalSim  # noqa: E402


class FakeClock:
    """Deterministic, advanceable monotonic clock for the simulator."""

    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


@pytest.fixture()
def clock():
    return FakeClock()


@pytest.fixture()
def sim(clock):
    econ = Economics(cold_start_s=8.0, kv_ttl_s=300.0, prefix_tokens=8)
    return MaxLocalSim("llm-sim", economics=econ, clock=clock,
                       replica=ReplicaState())


@pytest.fixture()
def client():
    """TestClient over the sim adapter (no GPU, deterministic)."""
    from starlette.testclient import TestClient

    from llm_app.main import get_app
    econ = Economics(cold_start_s=8.0, kv_ttl_s=300.0)
    app = get_app(MaxLocalSim("llm-sim", economics=econ, clock=FakeClock()))
    return TestClient(app)
