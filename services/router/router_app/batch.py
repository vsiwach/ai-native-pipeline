"""On-disk batch queue: jobs survive restarts; a worker pool drains them at
the policy's configured concurrency. This is the scale-to-zero story — batch
traffic tolerates cold backends, so it can wait for the cheapest capacity."""

import json
import os
import threading
import uuid
from pathlib import Path

PENDING, RUNNING, DONE, FAILED = "pending", "running", "done", "failed"


class BatchQueue:
    def __init__(self, queue_dir: Path):
        self.dir = Path(queue_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, job_id: str) -> Path:
        return self.dir / f"{job_id}.json"

    def _write_atomic(self, path: Path, job: dict) -> None:
        """Write via a temp file + rename so a concurrent reader never sees a
        half-written job (rename is atomic on POSIX)."""
        tmp = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        tmp.write_text(json.dumps(job))
        os.replace(tmp, path)

    def submit(self, model: str, payload: dict, headers: dict) -> str:
        job_id = uuid.uuid4().hex
        job = {"id": job_id, "model": model, "payload": payload,
               "headers": headers, "status": PENDING, "result": None,
               "error": None}
        self._write_atomic(self._path(job_id), job)
        return job_id

    def get(self, job_id: str) -> dict | None:
        path = self._path(job_id)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def claim(self) -> dict | None:
        """Atomically move one pending job to running. Tolerates a job file
        mid-write (skips it this pass; it'll be claimed next time)."""
        with self._lock:
            for path in sorted(self.dir.glob("*.json")):
                try:
                    job = json.loads(path.read_text())
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
                if job["status"] == PENDING:
                    job["status"] = RUNNING
                    self._write_atomic(path, job)
                    return job
        return None

    def finish(self, job_id: str, result: dict | None,
               error: str | None) -> None:
        job = self.get(job_id)
        if job is None:
            return
        job["status"] = FAILED if error else DONE
        job["result"] = result
        job["error"] = error
        self._write_atomic(self._path(job_id), job)


class BatchWorker:
    def __init__(self, queue: BatchQueue, process_job, concurrency: int = 2,
                 idle_wait_s: float = 0.25):
        """process_job: (job dict) -> result dict; raises on failure."""
        self.queue = queue
        self.process_job = process_job
        self.concurrency = concurrency
        self.idle_wait_s = idle_wait_s
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    def _loop(self):
        while not self._stop.is_set():
            job = self.queue.claim()
            if job is None:
                self._stop.wait(self.idle_wait_s)
                continue
            try:
                result = self.process_job(job)
                self.queue.finish(job["id"], result, None)
            except Exception as exc:  # noqa: BLE001 — job must record any failure
                self.queue.finish(job["id"], None, str(exc))

    def start(self) -> None:
        if self._threads:
            return
        for i in range(self.concurrency):
            t = threading.Thread(target=self._loop, daemon=True,
                                 name=f"batch-worker-{i}")
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        self._stop.set()
