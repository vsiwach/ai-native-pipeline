"""BasetenAdapter / VllmAdapter — measured economics, auth, stream, factory.

All I/O is injected (fake opener + fake clock): deterministic, no network,
no keys. Live wire behavior is exercised in the joint live session (F1).
"""

import json
import os
import unittest
from unittest import mock

from llm_app.adapter import ChatRequest
from llm_app.factory import build_adapter
from llm_app.openai_compat import BasetenAdapter, OpenAICompatAdapter, VllmAdapter


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


def sse(obj):
    return f"data: {json.dumps(obj)}"


def chunk(content=None, usage=None, chunk_id="chatcmpl-test"):
    body = {"id": chunk_id, "choices": []}
    if content is not None:
        body["choices"] = [{"index": 0, "delta": {"content": content}}]
    if usage is not None:
        body["usage"] = usage
    return body


def make_opener(clock, script):
    """script: list of (advance_seconds_before_yield, line). Records calls."""
    calls = []

    def opener(url, payload, headers, timeout):
        calls.append({"url": url, "payload": payload, "headers": headers})
        for advance, line in script:
            clock.advance(advance)
            yield line

    opener.calls = calls
    return opener


def request(stream=False):
    return ChatRequest.from_dict({
        "model": "qwen3-8b",
        "messages": [{"role": "user", "content": "hello there"}],
        "max_tokens": 8, "stream": stream,
    })


class MeasuredEconomicsTest(unittest.TestCase):
    def _adapter(self, script, usd_per_hour=0.60, cls=VllmAdapter):
        clock = FakeClock()
        opener = make_opener(clock, script)
        adapter = cls("qwen3-8b", base_url="http://pool:8000",
                      usd_per_hour=usd_per_hour, clock=clock, opener=opener)
        return adapter, opener

    def test_ttft_decode_and_cost_are_measured(self):
        script = [
            (0.100, sse(chunk("Hel"))),          # first token at 100ms
            (0.050, sse(chunk("lo"))),
            (0.050, sse(chunk(usage={"prompt_tokens": 3,
                                     "completion_tokens": 2}))),
            (0.0, "data: [DONE]"),
        ]
        adapter, _ = self._adapter(script)
        gen = adapter.generate(request())
        self.assertEqual(gen.text, "Hello")
        self.assertAlmostEqual(gen.plan.ttft_ms, 100.0, places=3)
        self.assertAlmostEqual(gen.plan.decode_ms, 100.0, places=3)
        self.assertEqual(gen.usage()["prompt_tokens"], 3)
        self.assertEqual(gen.usage()["completion_tokens"], 2)
        # 200ms of a $0.60/hr instance
        self.assertAlmostEqual(gen.plan.est_cost_usd, 0.60 * 0.2 / 3600, places=10)

    def test_usage_falls_back_to_estimates_when_absent(self):
        script = [(0.05, sse(chunk("word " * 8))), (0.0, "data: [DONE]")]
        adapter, _ = self._adapter(script)
        gen = adapter.generate(request())
        self.assertGreater(gen.usage()["completion_tokens"], 0)
        self.assertGreater(gen.usage()["prompt_tokens"], 0)

    def test_malformed_lines_never_crash_the_stream(self):
        script = [
            (0.01, ": keepalive"),
            (0.01, "data: {not json"),
            (0.01, sse(chunk("ok"))),
            (0.0, "data: [DONE]"),
        ]
        adapter, _ = self._adapter(script)
        self.assertEqual(adapter.generate(request()).text, "ok")


class AuthTest(unittest.TestCase):
    def test_baseten_requires_key_uses_bearer_and_predict_path(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BASETEN_API_KEY", None)
            with self.assertRaises(ValueError):
                BasetenAdapter("qwen3-8b", base_url="http://b")
        with mock.patch.dict(os.environ, {"BASETEN_API_KEY": "sk-test"}):
            clock = FakeClock()
            opener = make_opener(clock, [(0.0, "data: [DONE]")])
            adapter = BasetenAdapter(
                "qwen3-8b",
                base_url="https://model-x.api.baseten.co/environments/production",
                clock=clock, opener=opener)
            adapter.generate(request())
            self.assertEqual(opener.calls[0]["headers"]["Authorization"],
                             "Bearer sk-test")
            # custom Truss is invoked at /predict, not /v1/chat/completions
            self.assertTrue(opener.calls[0]["url"].endswith("/predict"))

    def test_baseten_healthz_never_wakes_the_pool(self):
        # health_path is None -> report proxy liveness, never ping Baseten
        # (a poll must not wake a scaled-to-zero replica and bill for it)
        with mock.patch.dict(os.environ, {"BASETEN_API_KEY": "k"}):
            adapter = BasetenAdapter(
                "qwen3-8b",
                base_url="https://model-x.api.baseten.co/environments/production")
            self.assertEqual(adapter.healthz(), {"status": "ok"})

    def test_vllm_key_optional_bearer_when_present(self):
        clock = FakeClock()
        opener = make_opener(clock, [(0.0, "data: [DONE]")])
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("VLLM_API_KEY", None)
            adapter = VllmAdapter("qwen3-8b", base_url="http://v",
                                  clock=clock, opener=opener)
            adapter.generate(request())
            self.assertNotIn("Authorization", opener.calls[0]["headers"])
        with mock.patch.dict(os.environ, {"VLLM_API_KEY": "tok"}):
            opener2 = make_opener(clock, [(0.0, "data: [DONE]")])
            adapter = VllmAdapter("qwen3-8b", base_url="http://v",
                                  clock=clock, opener=opener2)
            adapter.generate(request())
            self.assertEqual(opener2.calls[0]["headers"]["Authorization"],
                             "Bearer tok")

    def test_vllm_requests_stream_usage_baseten_does_not(self):
        clock = FakeClock()
        opener = make_opener(clock, [(0.0, "data: [DONE]")])
        VllmAdapter("m", base_url="http://v", clock=clock,
                    opener=opener).generate(request())
        self.assertEqual(opener.calls[0]["payload"]["stream_options"],
                         {"include_usage": True})
        with mock.patch.dict(os.environ, {"BASETEN_API_KEY": "k"}):
            opener2 = make_opener(clock, [(0.0, "data: [DONE]")])
            BasetenAdapter("m", base_url="http://b", clock=clock,
                           opener=opener2).generate(request())
            self.assertNotIn("stream_options", opener2.calls[0]["payload"])


class StreamRawTest(unittest.TestCase):
    def test_passthrough_normalizes_and_terminates(self):
        clock = FakeClock()
        opener = make_opener(clock, [
            (0.0, sse(chunk("hi"))),
            (0.0, json.dumps(chunk("!"))),   # upstream missing data: prefix
        ])
        adapter = VllmAdapter("m", base_url="http://v", clock=clock,
                              opener=opener)
        lines = list(adapter.stream_raw(request(stream=True)))
        self.assertTrue(all(l.startswith("data:") for l in lines))
        self.assertEqual(lines[-1], "data: [DONE]")

    def test_requires_base_url(self):
        with self.assertRaises(ValueError):
            VllmAdapter("m", base_url="")


class FactoryTest(unittest.TestCase):
    def test_engine_without_url_falls_back_to_sim(self):
        env = {"ENGINE": "vllm", "TARGET": "gpu", "MODEL_NAME": "qwen3-8b",
               "DECODE_MS_PER_TOKEN": "25.0"}
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("VLLM_BASE_URL", None)
            adapter = build_adapter()
        self.assertEqual(adapter.engine, "vllm")       # honest pool identity
        self.assertEqual(adapter.info()["backend"], "max-local-sim")
        self.assertEqual(adapter.econ.decode_ms_per_token, 25.0)

    def test_engine_with_url_builds_live_adapter(self):
        env = {"ENGINE": "vllm", "MODEL_NAME": "qwen3-8b",
               "VLLM_BASE_URL": "http://pod:8000",
               "POOL_USD_PER_HOUR": "0.60"}
        with mock.patch.dict(os.environ, env, clear=False):
            adapter = build_adapter()
        self.assertIsInstance(adapter, VllmAdapter)
        self.assertEqual(adapter.usd_per_hour, 0.60)

    def test_baseten_with_url_builds_live_adapter(self):
        env = {"ENGINE": "baseten", "MODEL_NAME": "qwen3-8b",
               "BASETEN_BASE_URL": "http://model.baseten.co/v1x",
               "BASETEN_API_KEY": "k"}
        with mock.patch.dict(os.environ, env, clear=False):
            adapter = build_adapter()
        self.assertIsInstance(adapter, BasetenAdapter)


if __name__ == "__main__":
    unittest.main()
