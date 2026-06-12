# inference — house-price-reg backend

Vendored from [eightBEC/fastapi-ml-skeleton](https://github.com/eightBEC/fastapi-ml-skeleton)
(Apache-2.0, see [LICENSE](LICENSE)) and adapted to this repo's inference
contract. Serves a California house-price linear regression — a stand-in for
any future model service; the contract matters, not the model.

## Contract surface (contracts/inference.openapi.yaml)

| Route | Auth | Returns |
|---|---|---|
| `GET /healthz` | none | `{"status":"ok"}` |
| `GET /v1/info` | none | `{"model":"house-price-reg","version":"1.0","tier":"standard","target":"cpu"}` |
| `POST /v1/predict` | `token` header = `INFERENCE_API_KEY` | `{"median_house_value": int, "currency":"USD"}` |

## Run

```bash
docker build -t inference:dev -f services/inference/Dockerfile .
docker run -d -p 8081:8080 -e INFERENCE_API_KEY=test inference:dev
curl localhost:8081/healthz
curl -X POST localhost:8081/v1/predict -H 'token: test' -H 'Content-Type: application/json' \
  -d @services/inference/docs/sample_payload.json
```

## Test

```bash
bazel test //services/inference/...
# or with a local 3.11+ venv:
pip install -r tools/requirements/inference_lock.txt
python -m pytest services/inference/tests -v
```

## Changes from upstream

- Package renamed `fastapi_skeleton` → `inference_app`; poetry packaging dropped
  (this repo owns packaging: requirements.txt + Dockerfile + Bazel).
- Routes adapted to the contract: `/api/health/heartbeat` → `/healthz`,
  `/api/model/predict` → `/v1/predict`, new `/v1/info`.
- API key env var renamed `API_KEY` → `INFERENCE_API_KEY`.
- Model path defaults to the bundled sample model; non-root Docker user +
  HEALTHCHECK added.
