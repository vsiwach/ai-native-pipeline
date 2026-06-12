# PHASE 1 — Vendor the dummy inference app

Paste everything below into Claude Code.

---

Vendor https://github.com/eightBEC/fastapi-ml-skeleton into this monorepo as our
first real inference backend. It serves a house-price regression model — treat it
as a stand-in for any future model service (the contract matters, not the model).

## Tasks
1. Clone the repo to a temp dir; copy only the application source (FastAPI app,
   model loading, sample model artifact, tests) into `services/inference/`.
   Drop their packaging/poetry config — we own packaging.
2. Restructure to our conventions:
   - `services/inference/inference_app/` (source), `services/inference/tests/`
   - `services/inference/requirements.txt` (pin fastapi, uvicorn, scikit-learn, joblib)
   - `services/inference/Dockerfile` (python:3.11-slim, non-root user, HEALTHCHECK)
3. Adapt endpoints to our contract (`contracts/inference.openapi.yaml` — create it):
   - `GET /healthz` -> `{"status":"ok"}`
   - `GET /v1/info` -> `{"model":"house-price-reg","version":"1.0","tier":"standard","target":"cpu"}`
   - `POST /v1/predict` -> keep their payload schema, namespaced under /v1
   - Keep their API-key auth; key from `INFERENCE_API_KEY` env var
4. Create `inference-registry.yaml` at repo root:
   ```yaml
   backends:
     house-price-reg:
       path: services/inference
       tier: standard
       target: cpu
       max_replicas: 3
       scale_to_zero: true
   ```
5. Add `BUILD.bazel` exposing tests (py_test) — container build stays in Docker/CI.
6. Make their tests pass under our layout; add a contract test asserting all three
   endpoints exist and return the documented shapes.

## Acceptance criteria (run these, show output)
- `bazel test //services/inference/...` green
- `docker build -t inference:dev -f services/inference/Dockerfile .` succeeds
- `docker run -d -p 8081:8080 -e INFERENCE_API_KEY=test inference:dev` then
  `curl localhost:8081/healthz` returns ok and `curl -X POST localhost:8081/v1/predict`
  (with sample payload + auth header) returns a prediction
- `git log` shows attribution: "vendored from eightBEC/fastapi-ml-skeleton (Apache-2.0)"
  — verify and preserve their LICENSE in services/inference/.
