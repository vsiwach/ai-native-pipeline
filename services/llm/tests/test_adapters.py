"""Adapter interface conformance: every adapter implements the uniform surface,
advertises honest capabilities, and refuses what it doesn't serve."""

import pytest

from llm_app.adapter import BackendAdapter, ChatMessage, ChatRequest
from llm_app.container import MaxContainer
from llm_app.sim import MaxLocalSim
from llm_app.sklearn_adapter import SklearnPredict


def test_sim_is_chat_capable_not_predict(sim):
    assert sim.capabilities() == {"chat"}
    with pytest.raises(NotImplementedError):
        sim.predict({})


def test_sklearn_is_predict_capable_not_chat():
    a = SklearnPredict("house-price-reg", base_url="http://inference:8080")
    assert a.capabilities() == {"predict"}
    assert a.engine == "sklearn"
    with pytest.raises(NotImplementedError):
        a.generate(ChatRequest("x", [ChatMessage("user", "hi")]))


def test_all_adapters_implement_the_interface(sim):
    sklearn = SklearnPredict("hp", "http://inference:8080")
    container = MaxContainer("m", base_url="http://gpu:8000", model_id="gemma")
    for a in (sim, sklearn, container):
        assert isinstance(a, BackendAdapter)
        assert isinstance(a.info(), dict)
        assert isinstance(a.capabilities(), set)
        assert a.info()["engine"] in ("max", "sklearn")


def test_container_requires_base_url():
    with pytest.raises(ValueError):
        MaxContainer("m", base_url="")


def test_info_reports_warm_state(sim):
    assert sim.info()["warm"] is False
    sim.generate(ChatRequest("llm-sim", [ChatMessage("user", "warm up")],
                             max_tokens=4, seed=1))
    assert sim.info()["warm"] is True
