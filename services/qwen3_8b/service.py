"""qwen3-8b — the baseten-mvp model, served by two pools behind one entry.

One registry backend ("qwen3-8b") with two replica endpoints in
routing-policy.yaml: the Baseten pool (Truss, engine=baseten) and the RunPod
vLLM pool (engine=vllm). Both run THIS image (the llm_app proxy) with
per-instance env:

  Baseten pool:  ENGINE=baseten BASETEN_BASE_URL=... POOL_USD_PER_HOUR=...
  vLLM pool:     ENGINE=vllm    VLLM_BASE_URL=...    POOL_USD_PER_HOUR=...
  (no *_BASE_URL → faithful local sim of that pool; no keys/GPU needed)

Edit THIS file, then `./dev sync`. Stdlib-only: `./dev sync` imports this
module, so declare the image, don't import the app.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "devkit"))

from manifest import Image, service  # noqa: E402

# The app code is services/llm's llm_app — this manifest is a pool-flavored
# deployment of it, not a fork.
APP = "services/llm"
PATH = "services/qwen3_8b"

image = (
    Image.debian_slim("3.11")
    .workdir("/srv")
    .copy(f"{APP}/requirements.txt", ".")
    .pip_install_requirements("requirements.txt")
    .copy(f"{APP}/llm_app", "./llm_app")
    .run("useradd --create-home --uid 10001 appuser")
    .user("appuser")
    .env(PORT="8080", ENGINE="vllm", TARGET="gpu", MODEL_NAME="qwen3-8b",
         MODEL_ID="Qwen/Qwen3-8B", COLD_START_S="25.0", KV_TTL_S="300.0",
         DECODE_MS_PER_TOKEN="25.0", PREFILL_MS_PER_TOKEN="0.3",
         USD_PER_1M_COMPLETION="0.90")
    .expose(8080)
    .healthcheck(
        'python -c "import urllib.request;'
        "urllib.request.urlopen('http://127.0.0.1:8080/healthz')\"",
        interval="10s", timeout="3s", start_period="10s",
    )
    .cmd(["uvicorn", "llm_app.main:app", "--host", "0.0.0.0", "--port", "8080"])
)

SERVICE = service(
    name="qwen3-8b",
    path=PATH,
    tier="realtime",     # voice SLO tier: TTFT p99<500ms, TPOT p99<60ms
    target="gpu",
    engine="vllm",       # default instance engine; baseten pool overrides env
    model_id="Qwen/Qwen3-8B",
    cold_start_s=25.0,
    kv_ttl_s=300.0,
    max_replicas=4,
    scale_to_zero=True,
    image=image,
)
