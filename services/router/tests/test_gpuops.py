"""GpuOps unit tests — mocked RunPod API, temp ledger, real (instant)
subprocess for Job. The spend guard and ledger bookkeeping are the load-
bearing parts: a launch must refuse past the cap, append an open entry,
and terminate must close it."""

import json
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from router_app import gpuops as gpuops_mod
from router_app.gpuops import GpuOps, Job


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload


class GpuOpsTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "deploy" / "runpod").mkdir(parents=True)
        self._write_ledger(cap=40.0, entries=[])
        self.events = []
        self.ops = GpuOps("key", self.root,
                          emit=lambda kind, **f: self.events.append((kind, f)))

    def _write_ledger(self, cap, entries):
        (self.root / "deploy" / "runpod" / "spend-ledger.json").write_text(
            json.dumps({"cap_usd": cap, "entries": entries}))

    def test_launch_appends_open_ledger_entry(self):
        created = {"id": "pod123", "costPerHr": 1.39}
        with mock.patch.object(gpuops_mod.httpx, "request",
                               return_value=FakeResponse(200, created)) as rq:
            out = self.ops.launch("a100")
        self.assertEqual(out["id"], "pod123")
        self.assertIn("proxy.runpod.net", out["url"])
        body = rq.call_args.kwargs["json"]
        self.assertEqual(body["imageName"], "modular/max-nvidia-full:26.4.0")
        self.assertNotIn("latest", body["imageName"])  # pinned — friction #16
        led = json.loads((self.root / "deploy" / "runpod" /
                          "spend-ledger.json").read_text())
        self.assertEqual(len(led["entries"]), 1)
        self.assertIsNone(led["entries"][0]["end_ts"])
        self.assertEqual(led["entries"][0]["usd_per_hr"], 1.39)
        self.assertIn(("gpu_ops", {"action": "launch", "pod_kind": "a100",
                                   "pod": "pod123", "usd_hr": 1.39}),
                      self.events)

    def test_budget_guard_refuses_launch(self):
        # 100 hours of an open $1/hr entry ≈ $100 spent > $40 cap
        self._write_ledger(cap=40.0, entries=[{
            "what": "runpod X pod old1", "start_ts": time.time() - 360000,
            "usd_per_hr": 1.0, "end_ts": None}])
        with mock.patch.object(gpuops_mod.httpx, "request") as rq:
            with self.assertRaisesRegex(RuntimeError, "BUDGET GUARD"):
                self.ops.launch("a100")
            rq.assert_not_called()   # refused BEFORE any money moved

    def test_terminate_closes_ledger_entry(self):
        self._write_ledger(cap=40.0, entries=[{
            "what": "runpod A100 pod pod123", "start_ts": time.time() - 60,
            "usd_per_hr": 1.39, "end_ts": None}])
        with mock.patch.object(gpuops_mod.httpx, "request",
                               return_value=FakeResponse(200, {})):
            out = self.ops.terminate("pod123")
        self.assertTrue(out["terminated"])
        led = json.loads((self.root / "deploy" / "runpod" /
                          "spend-ledger.json").read_text())
        self.assertIsNotNone(led["entries"][0]["end_ts"])

    def test_list_pods_filters_prefix_and_probes(self):
        pods = [
            {"id": "p1", "name": "modular-demo-a100", "costPerHr": 1.39,
             "runtime": {"uptimeInSeconds": 100},
             "machine": {"gpuTypeId": "NVIDIA A100 80GB PCIe"},
             "imageName": "modular/max-nvidia-full:26.4.0"},
            {"id": "p2", "name": "unrelated-pod", "costPerHr": 9.9},
        ]
        with mock.patch.object(gpuops_mod.httpx, "request",
                               return_value=FakeResponse(200, pods)), \
             mock.patch.object(self.ops, "_probe", return_value=True):
            out = self.ops.list_pods()
        self.assertEqual([p["id"] for p in out], ["p1"])
        self.assertTrue(out[0]["ready"])
        self.assertEqual(out[0]["kind"], "a100")

    def test_runpod_error_raises(self):
        with mock.patch.object(gpuops_mod.httpx, "request",
                               return_value=FakeResponse(500, {"err": "x"})):
            with self.assertRaisesRegex(RuntimeError, "runpod"):
                self.ops.list_pods()

    def test_job_tail_and_status(self):
        job = Job("echo", [sys.executable, "-c",
                           "print('line1'); print('line2')"], Path("."))
        deadline = time.monotonic() + 10
        while job.status()["running"] and time.monotonic() < deadline:
            time.sleep(0.05)
        s = job.status()
        self.assertFalse(s["running"])
        self.assertEqual(s["rc"], 0)
        self.assertEqual(s["tail"], ["line1", "line2"])


if __name__ == "__main__":
    unittest.main()
