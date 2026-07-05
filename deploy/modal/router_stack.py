# The whole certified-migration demo stack as ONE public Modal web app, so
# the console at modular-certified-migration.vercel.app can be DRIVEN live
# by anyone with the dev token — no laptop router required.
#
#   llm-sim (:8111)  <- incumbent's upstream (economics simulator)
#   docs-assist primary (:8112) + candidate (:8113, runtime-switchable)
#   router (:8114)   <- the ONLY exposed port (repo architecture rule)
#
# The router carries the RunPod key + dev token via a Modal Secret; GPU
# launches from the console go through its ledger budget guard. State
# (shadow logs, certs, ledger deltas) lives in the container — ephemeral by
# design; the durable evidence path stays the repo. Scale-to-zero after 10
# idle minutes: a parked demo costs $0.
#
#   modal secret create certified-migration-router \
#       RUNPOD_API_KEY=... ROUTER_DEV_TOKEN=...
#   modal deploy deploy/modal/router_stack.py
#   -> console: https://modular-certified-migration.vercel.app/demo.html\
#        ?router=https://<workspace>--certified-migration-router-serve.modal.run&token=<token>

from pathlib import Path

import modal

# Resolves to the repo checkout at deploy time (image build inputs); the
# module ALSO imports inside the container at /root/router_stack.py, where
# only the baked /repo tree exists.
try:
    REPO = Path(__file__).resolve().parents[2]
except IndexError:
    REPO = Path("/repo")
MAX_ENDPOINT = "https://vsiwach--max-qwen25-serve.modal.run/v1"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("fastapi==0.115.12", "uvicorn==0.34.2", "httpx==0.28.1",
                 "pydantic==2.11.4", "PyYAML==6.0.2")
    .add_local_dir(REPO / "services" / "router" / "router_app",
                   "/repo/services/router/router_app")
    .add_local_dir(REPO / "services" / "docs_assist",
                   "/repo/services/docs_assist")   # includes kb/*.sqlite
    .add_local_dir(REPO / "services" / "llm" / "llm_app",
                   "/repo/services/llm/llm_app")
    .add_local_dir(REPO / "tools" / "devkit", "/repo/tools/devkit")
    .add_local_file(REPO / "tools" / "bench.py", "/repo/tools/bench.py")
    .add_local_file(REPO / "tools" / "certify.py", "/repo/tools/certify.py")
    .add_local_file(REPO / "dev", "/repo/dev")
    .add_local_dir(REPO / "evals", "/repo/evals")
    .add_local_file(REPO / "inference-registry.yaml",
                    "/repo/inference-registry.yaml")
    .add_local_file(REPO / "deploy" / "modal" / "routing-policy.stack.yaml",
                    "/repo/routing-policy.yaml")
    .add_local_file(REPO / "deploy" / "runpod" / "spend-ledger.json",
                    "/repo/deploy/runpod/spend-ledger.json")
)

app = modal.App("certified-migration-router")


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("certified-migration-router")],
    timeout=60 * 60,
    scaledown_window=600,
    memory=2048,
    # the router is stateful (shadow logs, loadgen run, ledger, releases) —
    # one container, always; a second would split the demo's state
    max_containers=1,
)
@modal.concurrent(max_inputs=64)
@modal.web_server(8114, startup_timeout=180)
def serve():
    import os
    import subprocess

    os.chdir("/repo")
    os.chmod("/repo/dev", 0o755)
    base = dict(os.environ, PYTHONPATH="/repo")

    def spawn(cmd, cwd, **env):
        subprocess.Popen(cmd, cwd=cwd, env={**base, **env})

    spawn(["python", "-m", "uvicorn", "llm_app.main:app", "--port", "8111",
           "--log-level", "warning"], "/repo/services/llm",
          ENGINE="max", TARGET="cpu", MODEL_NAME="llm-sim",
          COLD_START_S="1.0")
    for port in ("8112", "8113"):
        spawn(["python", "-m", "uvicorn", "app:app", "--port", port,
               "--log-level", "warning"], "/repo/services/docs_assist",
              UPSTREAM_BASE_URL="http://127.0.0.1:8111/v1",
              UPSTREAM_MODEL="llm-sim",
              KB_INDEX="/repo/services/docs_assist/kb/modular_kb.sqlite",
              DEV_UPSTREAM_SWITCH="1")
    spawn(["python", "-m", "uvicorn", "router_app.main:app",
           "--host", "0.0.0.0", "--port", "8114", "--log-level", "warning"],
          "/repo/services/router",
          REGISTRY_PATH="/repo/inference-registry.yaml",
          ROUTING_POLICY_PATH="/repo/routing-policy.yaml",
          SHADOW_LOG_DIR="/repo/shadow-logs",
          ROUTER_QUEUE_DIR="/tmp/router-queue",
          BENCH_REPORTS_DIR="/repo/bench-reports",
          GPUOPS_ROOT="/repo",
          GPU_MODAL_URL=MAX_ENDPOINT,
          LOADGEN_TARGET="http://127.0.0.1:8114",
          INCIDENT_AGENT="0",
          ROUTER_CORS_ORIGINS="*")
