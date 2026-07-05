"""ShadowMirror unit tests — mocked httpx, no sockets. The mirror must:
run from threads without an event loop (the chat proxy lives in a
threadpool), never surface candidate failures, strip `stream` before
mirroring, and land every record in the JSONL log before flush() returns."""

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from router_app import shadow as shadow_mod
from router_app.shadow import ShadowMirror


class FakeResponse:
    status_code = 200

    def __init__(self, content="candidate says hi [1]", citations='[{"n":1}]'):
        self._content = content
        self.headers = {"X-Citations": citations}

    def json(self):
        return {"choices": [{"message": {"role": "assistant",
                                         "content": self._content}}],
                "usage": {"completion_tokens": 4}}


class FakeClient:
    """Stands in for httpx.AsyncClient; records calls."""
    calls: list = []
    fail = False

    def __init__(self, *a, **kw):
        pass

    async def post(self, url, json=None, headers=None):
        type(self).calls.append({"url": url, "json": json, "headers": headers})
        if type(self).fail:
            raise RuntimeError("candidate unreachable")
        return FakeResponse()

    async def aclose(self):
        pass


class TestShadowMirror(unittest.TestCase):
    def setUp(self):
        FakeClient.calls = []
        FakeClient.fail = False
        self.patcher = mock.patch.object(shadow_mod.httpx, "AsyncClient",
                                         FakeClient)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def mirror(self, **kw):
        return ShadowMirror(route="docs-assist",
                            candidate_url="http://cand:8080/v1",
                            log_dir=self.tmp.name, **kw)

    def log_records(self, m):
        return [json.loads(l) for l in
                Path(m.log_path).read_text().splitlines()]

    def test_submit_from_sync_thread_writes_log(self):
        m = self.mirror()
        payload = {"messages": [{"role": "user", "content": "q?"}],
                   "stream": True}
        primary = {"choices": [{"message": {"role": "assistant",
                                            "content": "primary answer"}}]}
        m.submit(payload, primary)          # no running loop in this thread
        self.assertTrue(m.flush(timeout_s=5))
        self.assertEqual((m.submitted, m.completed, m.failed), (1, 1, 0))
        recs = self.log_records(m)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["route"], "docs-assist")
        self.assertEqual(recs[0]["primary"]["content"], "primary answer")
        self.assertEqual(recs[0]["candidate"]["content"],
                         "candidate says hi [1]")
        self.assertEqual(recs[0]["candidate"]["citations"], '[{"n":1}]')
        # the caller's dict must not be mutated; the mirrored copy must not
        # ask the candidate to stream (shadow compares full completions)
        self.assertIn("stream", payload)
        self.assertNotIn("stream", FakeClient.calls[0]["json"])
        self.assertEqual(FakeClient.calls[0]["url"],
                         "http://cand:8080/v1/chat/completions")

    def test_candidate_failure_is_recorded_never_raised(self):
        FakeClient.fail = True
        m = self.mirror()
        m.submit({"messages": []}, {})      # must not raise
        self.assertTrue(m.flush(timeout_s=5))
        self.assertEqual((m.completed, m.failed), (0, 1))
        recs = self.log_records(m)
        self.assertIn("error", recs[0]["candidate"])

    def test_stats_shape(self):
        m = self.mirror()
        for _ in range(3):
            m.submit({"messages": []}, {})
        m.flush(timeout_s=5)
        s = m.stats()
        self.assertEqual(s["route"], "docs-assist")
        self.assertEqual(s["submitted"], 3)
        self.assertEqual(s["completed"], 3)
        self.assertTrue(s["log"].endswith("docs-assist.shadow.jsonl"))

    def test_api_key_header(self):
        m = self.mirror(api_key="sk-test")
        m.submit({"messages": []}, {})
        m.flush(timeout_s=5)
        self.assertEqual(FakeClient.calls[0]["headers"],
                         {"Authorization": "Bearer sk-test"})


if __name__ == "__main__":
    unittest.main()
