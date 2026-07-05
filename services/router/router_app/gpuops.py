"""GPU pool ops — the dev surface behind the console's GPU card.

The certified-migration story needs rented GPU pods (NVIDIA + AMD) and the
console is the operator surface, so the router wraps the RunPod REST API
server-side: the API key lives in the router's env (RUNPOD_API_KEY), never
in the browser. Same dev-surface family as /v1/dev/chaos and /v1/dev/loadgen.

Spend discipline is enforced HERE, not in the UI: every launch runs the
repo's ledger budget guard (deploy/runpod/spend-ledger.json, hard cap) and
appends an open entry; terminate closes it. Images are PINNED (an unpinned
:latest presents as rented-but-dead pods — FRICTION_LOG #16).

bench/certify shell out to the repo's own tools (`tools/bench.py`,
`./dev certify`) as background jobs — the console polls their tail. This is
a LOCAL-DEV surface by design: it exists only when RUNPOD_API_KEY is set
and GPUOPS_ROOT points at a repo checkout.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

import httpx

RUNPOD_API = "https://rest.runpod.io/v1"
POD_PREFIX = "modular-demo-"

# Pinned, known-good configs — same model, same MAX version, two vendors.
KINDS = {
    "a100": {
        "gpu": "NVIDIA A100 80GB PCIe",
        "image": "modular/max-nvidia-full:26.4.0",
        "pool": "a100",
        "label": "A100 80GB (NVIDIA)",
        "est_usd_hr": 1.9,
    },
    "mi300x": {
        "gpu": "AMD Instinct MI300X OAM",
        "image": "modular/max-amd:26.4.0",
        "pool": "mi300x",
        "label": "MI300X 192GB (AMD)",
        "est_usd_hr": 2.5,
    },
}
MODEL = "Qwen/Qwen2.5-14B-Instruct"


class Job:
    """A background subprocess with a rolling output tail."""

    def __init__(self, name: str, cmd: list[str], cwd: Path):
        self.name = name
        self.cmd = cmd
        self.started = time.time()
        self.tail: deque[str] = deque(maxlen=8)
        self._proc = subprocess.Popen(
            cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True)
        threading.Thread(target=self._pump, daemon=True,
                         name=f"gpuops-{name}").start()

    def _pump(self) -> None:
        for line in self._proc.stdout:
            self.tail.append(line.rstrip()[:200])
        self._proc.wait()

    def status(self) -> dict:
        rc = self._proc.poll()
        return {"name": self.name, "running": rc is None, "rc": rc,
                "elapsed_s": round(time.time() - self.started, 1),
                "tail": list(self.tail)}


class GpuOps:
    def __init__(self, api_key: str, root: Path, emit=None):
        self.api_key = api_key
        self.root = Path(root)
        self.emit = emit or (lambda kind, **f: None)
        self.jobs: dict[str, Job] = {}

    # ---- RunPod plumbing ---------------------------------------------------
    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        r = httpx.request(
            method, f"{RUNPOD_API}{path}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=body, timeout=30)
        if r.status_code >= 400:
            raise RuntimeError(f"runpod {method} {path} -> {r.status_code}: "
                               f"{r.text[:200]}")
        return r.json() if r.text else {}

    @staticmethod
    def pod_url(pod_id: str) -> str:
        return f"https://{pod_id}-8000.proxy.runpod.net/v1"

    def _probe(self, pod_id: str) -> bool:
        try:
            return httpx.get(f"{self.pod_url(pod_id)}/models",
                             timeout=4).status_code == 200
        except httpx.HTTPError:
            return False

    # ---- ledger (shared with deploy/runpod/pod.py) --------------------------
    @property
    def ledger_path(self) -> Path:
        return self.root / "deploy" / "runpod" / "spend-ledger.json"

    def _ledger(self) -> dict:
        return json.loads(self.ledger_path.read_text())

    def budget(self) -> dict:
        led = self._ledger()
        now = time.time()
        spent = sum(((e["end_ts"] or now) - e["start_ts"]) / 3600
                    * e["usd_per_hr"] for e in led["entries"])
        return {"cap_usd": led["cap_usd"], "spent_usd": round(spent, 2),
                "remaining_usd": round(led["cap_usd"] - spent, 2)}

    # ---- operations ---------------------------------------------------------
    def list_pods(self) -> list[dict]:
        pods = self._call("GET", "/pods")
        out = []
        for p in pods if isinstance(pods, list) else pods.get("pods", []):
            if not (p.get("name") or "").startswith(POD_PREFIX):
                continue
            runtime = p.get("runtime") or {}
            pod_id = p["id"]
            kind = p["name"].removeprefix(POD_PREFIX)
            out.append({
                "id": pod_id,
                "kind": kind,
                "gpu": (p.get("machine") or {}).get("gpuTypeId"),
                "usd_hr": p.get("costPerHr"),
                "uptime_s": runtime.get("uptimeInSeconds"),
                "ready": self._probe(pod_id),
                "url": self.pod_url(pod_id),
                "image": p.get("imageName"),
            })
        return out

    def launch(self, kind: str) -> dict:
        cfg = KINDS[kind]
        b = self.budget()
        projected = b["spent_usd"] + 1.0 * cfg["est_usd_hr"]  # 1h horizon
        if projected > b["cap_usd"]:
            raise RuntimeError(
                f"BUDGET GUARD: spent ${b['spent_usd']} + 1h*"
                f"${cfg['est_usd_hr']}/hr projects ${projected:.2f} > cap "
                f"${b['cap_usd']}")
        pod = self._call("POST", "/pods", {
            "name": f"{POD_PREFIX}{kind}",
            "imageName": cfg["image"],
            "gpuTypeIds": [cfg["gpu"]],
            "gpuCount": 1,
            "cloudType": "SECURE",
            "containerDiskInGb": 80,
            "volumeInGb": 0,
            "ports": ["8000/http"],
            "dockerStartCmd": ["--model", MODEL],
        })
        led = self._ledger()
        led["entries"].append({
            "what": f"runpod {cfg['gpu']} pod {pod['id']} (console launch)",
            "start_ts": time.time(),
            "usd_per_hr": float(pod.get("costPerHr") or cfg["est_usd_hr"]),
            "end_ts": None,
        })
        self.ledger_path.write_text(json.dumps(led, indent=2))
        self.emit("gpu_ops", action="launch", pod_kind=kind, pod=pod["id"],
                  usd_hr=pod.get("costPerHr"))
        return {"id": pod["id"], "usd_hr": pod.get("costPerHr"),
                "url": self.pod_url(pod["id"])}

    def terminate(self, pod_id: str) -> dict:
        self._call("DELETE", f"/pods/{pod_id}")
        led = self._ledger()
        for e in led["entries"]:
            if pod_id in e["what"] and not e.get("end_ts"):
                e["end_ts"] = time.time()
        self.ledger_path.write_text(json.dumps(led, indent=2))
        self.emit("gpu_ops", action="terminate", pod=pod_id)
        return {"id": pod_id, "terminated": True, "budget": self.budget()}

    def start_bench(self, pod: dict, reports_dir: str) -> dict:
        pool = KINDS.get(pod["kind"], {}).get("pool", pod["kind"])
        out = Path(reports_dir) / f"{pool}.json"
        cmd = [sys.executable, "tools/bench.py",
               "--base-url", pod["url"], "--model", MODEL,
               "--pool-usd-hr", str(pod["usd_hr"]),
               "--pool-name", pool, "--profile", "docs-agent",
               "--requests", "40", "--concurrency", "4",
               "--slo-ttft-ms", "800", "--out", str(out)]
        self.jobs["bench"] = Job("bench", cmd, self.root)
        self.emit("gpu_ops", action="bench", pod=pod["id"], pool=pool)
        return self.jobs["bench"].status()

    def start_certify(self, pool: str, shadow_log: str, policy_path: str,
                      image: str) -> dict:
        report = str(Path(os.environ.get("BENCH_REPORTS_DIR",
                                         "bench-reports")) / f"{pool}.json")
        build = f"{MODEL.split('/')[-1].lower()}@{image.split(':')[-1]}+{pool}"
        cmd = ["./dev", "certify", "run",
               "--evals", "evals/docs_qa.jsonl",
               "--shadow-log", shadow_log,
               "--bench-report", report,
               "--route-config", policy_path,
               "--model-build", build,
               "--gate-parity", "0.90", "--slo-ttft-ms", "800",
               "--out", "certs"]
        self.jobs["certify"] = Job("certify", cmd, self.root)
        self.emit("gpu_ops", action="certify", pool=pool, build=build)
        return self.jobs["certify"].status()

    def jobs_status(self) -> dict:
        return {name: job.status() for name, job in self.jobs.items()}
