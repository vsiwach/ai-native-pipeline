"""Batch queue lifecycle: submit -> pending -> worker drains -> done, plus
failure recording and queue-routing of batch-tier predict calls."""

import threading

from router_app.batch import DONE, FAILED, PENDING, BatchQueue, BatchWorker

PAYLOAD = {"median_income_in_block": 8.3252}


def test_predict_with_batch_tier_is_enqueued(router_client):
    resp = router_client.post(
        "/v1/predict?model=house-price-reg&tier=batch", json=PAYLOAD)
    assert resp.status_code == 202
    assert resp.json()["status"] == "pending"
    assert resp.json()["poll"].startswith("/v1/batch/")


def test_batch_submit_poll_complete(router_client):
    resp = router_client.post("/v1/batch?model=house-price-reg", json=PAYLOAD)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    status = router_client.get(f"/v1/batch/{job_id}").json()
    assert status["status"] == PENDING

    # drain synchronously — same code path the worker thread runs
    job = router_client.state.queue.claim()
    result = router_client.state.process_batch_job(job)
    router_client.state.queue.finish(job["id"], result, None)

    status = router_client.get(f"/v1/batch/{job_id}").json()
    assert status["status"] == DONE
    assert status["result"]["prediction"] == {"median_house_value": 123,
                                              "currency": "USD"}
    assert status["result"]["backend"] == "local-docker"


def test_batch_job_failure_recorded(router_client):
    router_client.handler.healthy = False
    router_client.state.poller.poll_once()
    resp = router_client.post("/v1/batch?model=house-price-reg", json=PAYLOAD)
    job_id = resp.json()["job_id"]

    job = router_client.state.queue.claim()
    try:
        result = router_client.state.process_batch_job(job)
        error = None
    except Exception as exc:  # noqa: BLE001 — mirroring the worker loop
        result, error = None, str(exc)
    router_client.state.queue.finish(job["id"], result, error)

    status = router_client.get(f"/v1/batch/{job_id}").json()
    assert status["status"] == FAILED
    assert status["error"]


def test_unknown_batch_job_404(router_client):
    resp = router_client.get("/v1/batch/nope")
    assert resp.status_code == 404


def test_worker_thread_drains_queue(tmp_path):
    queue = BatchQueue(tmp_path / "q")
    done = threading.Event()

    def process(job):
        done.set()
        return {"ok": True, "echo": job["payload"]}

    worker = BatchWorker(queue, process, concurrency=1, idle_wait_s=0.01)
    job_id = queue.submit("m", {"x": 1}, {})
    worker.start()
    assert done.wait(timeout=5)
    worker.stop()
    for _ in range(100):
        if queue.get(job_id)["status"] == DONE:
            break
    assert queue.get(job_id)["status"] == DONE
    assert queue.get(job_id)["result"]["echo"] == {"x": 1}


def test_queue_survives_restart(tmp_path):
    q1 = BatchQueue(tmp_path / "q")
    job_id = q1.submit("m", {"x": 1}, {})
    q2 = BatchQueue(tmp_path / "q")  # same dir, fresh instance
    assert q2.get(job_id)["status"] == PENDING
