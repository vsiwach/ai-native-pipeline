"""llm-sim — an LLM serving backend, resources & image as code.

Default engine is the no-GPU MAX simulator (engine=max, target=cpu). Flip to a
real `max serve` by setting target=gpu and MAX_BASE_URL (see README) — the
router and this app are unchanged. Edit THIS file, then `./dev sync`.

Stdlib-only: `./dev sync` imports this module, so declare the image, don't
import the app or model libraries.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "devkit"))

from manifest import Image, service  # noqa: E402

PATH = "services/llm"

image = (
    Image.debian_slim("3.11")
    .workdir("/srv")
    .copy(f"{PATH}/requirements.txt", ".")
    .pip_install_requirements("requirements.txt")
    .copy(f"{PATH}/llm_app", "./llm_app")
    .run("useradd --create-home --uid 10001 appuser")
    .user("appuser")
    .env(PORT="8080", ENGINE="max", TARGET="cpu", MODEL_NAME="llm-sim",
         COLD_START_S="8.0", KV_TTL_S="300.0")
    .expose(8080)
    .healthcheck(
        'python -c "import urllib.request;'
        "urllib.request.urlopen('http://127.0.0.1:8080/healthz')\"",
        interval="10s", timeout="3s", start_period="10s",
    )
    .cmd(["uvicorn", "llm_app.main:app", "--host", "0.0.0.0", "--port", "8080"])
)

SERVICE = service(
    name="llm-sim",
    path=PATH,
    tier="realtime",     # realtime | standard | batch
    target="cpu",        # cpu (sim) | gpu (real max serve)
    engine="max",        # max | sklearn
    model_id="google/gemma-3-12b-it",  # what a real `max serve` would load
    cold_start_s=8.0,
    kv_ttl_s=300.0,
    max_replicas=3,
    scale_to_zero=True,
    image=image,
)
