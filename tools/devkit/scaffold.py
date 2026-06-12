"""Scaffold a new inference service with every artifact the conventions require:

  services/<name>/app.py          stdlib HTTP service implementing the contract
  services/<name>/tests/          unittest suite (Bazel AND plain-python runnable)
  services/<name>/Dockerfile
  services/<name>/BUILD.bazel
  services/<name>/README.md
  services/<name>/requirements.txt (empty — pip deps go here, Docker-only)
  inference-registry.yaml entry
  .github/workflows/service-<name>.yml  (container /healthz CI job)

The generated service is stdlib-only so it builds under Bazel with no pip deps.
Swap app.py for FastAPI later if you like — keep the three contract routes.
"""

import re
from pathlib import Path

from registry import add as registry_add

NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,40}$")


def _app_py(name: str, tier: str) -> str:
    return f'''"""{name} — inference backend implementing contracts/inference.openapi.yaml.

Stdlib-only. Routes: GET /healthz, GET /v1/info, POST /v1/predict.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL_NAME = "{name}"
MODEL_VERSION = os.environ.get("MODEL_VERSION", "0.1.0")
COST_TIER = "{tier}"


def predict(payload: dict) -> dict:
    """Replace this stub with real model inference.

    Contract: accepts a JSON object, returns a JSON-serializable dict.
    """
    inputs = payload.get("inputs")
    if inputs is None:
        raise ValueError("missing 'inputs' field")
    return {{"model": MODEL_NAME, "version": MODEL_VERSION, "outputs": inputs}}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._send(200, {{"status": "ok"}})
        elif self.path == "/v1/info":
            self._send(200, {{"model": MODEL_NAME, "version": MODEL_VERSION,
                              "cost_tier": COST_TIER}})
        else:
            self._send(404, {{"error": "not found"}})

    def do_POST(self) -> None:
        if self.path != "/v1/predict":
            self._send(404, {{"error": "not found"}})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{{}}")
            self._send(200, predict(payload))
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(400, {{"error": str(exc)}})

    def log_message(self, *args) -> None:  # quiet by default
        pass


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"{{MODEL_NAME}} listening on :{{port}}")
    server.serve_forever()


if __name__ == "__main__":
    main()
'''


def _test_py(name: str) -> str:
    return f'''"""Tests for the {name} service. Runs via Bazel and plain python."""

import json
import sys
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app  # noqa: E402


class PredictTest(unittest.TestCase):
    def test_predict_echoes_inputs(self):
        result = app.predict({{"inputs": [1, 2, 3]}})
        self.assertEqual(result["outputs"], [1, 2, 3])
        self.assertEqual(result["model"], "{name}")

    def test_predict_rejects_missing_inputs(self):
        with self.assertRaises(ValueError):
            app.predict({{}})


class ContractTest(unittest.TestCase):
    """Boot the real server and exercise the three contract routes."""

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.base = f"http://127.0.0.1:{{cls.server.server_address[1]}}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _get(self, path):
        with urllib.request.urlopen(self.base + path) as resp:
            return resp.status, json.loads(resp.read())

    def test_healthz(self):
        status, body = self._get("/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_info_declares_contract_fields(self):
        status, body = self._get("/v1/info")
        self.assertEqual(status, 200)
        for field in ("model", "version", "cost_tier"):
            self.assertIn(field, body)

    def test_predict_roundtrip(self):
        req = urllib.request.Request(
            self.base + "/v1/predict",
            data=json.dumps({{"inputs": "hello"}}).encode(),
            headers={{"Content-Type": "application/json"}},
        )
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read())
        self.assertEqual(resp.status, 200)
        self.assertEqual(body["outputs"], "hello")


if __name__ == "__main__":
    unittest.main()
'''


def _dockerfile(name: str) -> str:
    return f"""FROM python:3.11-slim
WORKDIR /srv
COPY services/{name}/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/{name}/app.py .
ENV PORT=8080
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s CMD \\
  python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/healthz')"
CMD ["python", "app.py"]
"""


def _build_bazel(name: str) -> str:
    target = name.replace("-", "_")
    return f"""# Stdlib-only targets — pip deps live in requirements.txt (Docker layer only).
py_library(
    name = "{target}_lib",
    srcs = ["app.py"],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "{target}",
    srcs = ["app.py"],
    main = "app.py",
)

py_test(
    name = "{target}_test",
    srcs = ["tests/test_app.py"],
    main = "tests/test_app.py",
    deps = [":{target}_lib"],
)
"""


def _service_readme(name: str, tier: str, target: str) -> str:
    return f"""# {name}

Inference backend ({tier} tier, {target}). Implements the contract in
`contracts/inference.openapi.yaml`: `GET /healthz`, `GET /v1/info`,
`POST /v1/predict`.

## Run locally
```
python3 services/{name}/app.py                 # bare
./dev run {name}                               # in Docker, with healthz probe
```

## Test
```
./dev test                                     # bazel or unittest fallback
python3 services/{name}/tests/test_app.py      # just this service
```

The predict logic lives in `app.predict()` — swap the stub for a real model
and keep the signature. Pip dependencies go in `requirements.txt` (consumed by
the Dockerfile only; Bazel targets stay stdlib-only).
"""


def _ci_workflow(name: str) -> str:
    return f"""name: service-{name}
on:
  pull_request:
    paths: ["services/{name}/**"]
  push:
    branches: [main]
    paths: ["services/{name}/**"]

jobs:
  container-healthz:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build container
        run: docker build -f services/{name}/Dockerfile -t {name}:ci .
      - name: Boot and probe /healthz
        run: |
          docker run -d --rm -p 8080:8080 --name {name}-ci {name}:ci
          for i in $(seq 1 20); do
            if curl -fsS http://127.0.0.1:8080/healthz; then exit 0; fi
            sleep 1
          done
          docker logs {name}-ci
          exit 1
      - name: Unit tests
        run: python3 services/{name}/tests/test_app.py
"""


def create_service(repo_root: Path, name: str, tier: str, target: str) -> list[Path]:
    """Generate all artifacts for a new service. Returns the created paths."""
    if not NAME_RE.match(name):
        raise ValueError(
            f"invalid service name {name!r}: lowercase letters, digits, hyphens"
        )
    service_dir = repo_root / "services" / name
    if service_dir.exists():
        raise ValueError(f"services/{name} already exists")

    files = {
        service_dir / "app.py": _app_py(name, tier),
        service_dir / "tests" / "__init__.py": "",
        service_dir / "tests" / "test_app.py": _test_py(name),
        service_dir / "Dockerfile": _dockerfile(name),
        service_dir / "BUILD.bazel": _build_bazel(name),
        service_dir / "README.md": _service_readme(name, tier, target),
        service_dir / "requirements.txt": "# pip deps for the Docker image only\n",
        repo_root / ".github" / "workflows" / f"service-{name}.yml": _ci_workflow(name),
    }
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    registry_add(repo_root, name, tier, target, f"services/{name}")
    return list(files)
