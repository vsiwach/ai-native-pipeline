"""model_apis — every Baseten hosted Model API, as one catalog-driven pool.

One manifest, MANY registry backends: this file reads the catalog snapshot
(deploy/baseten/model-apis.json, generated from the live /v1/models listing by
`python3 deploy/baseten/manage.py catalog`) and emits one Service per model.
Deploying another library model (Kimi K2.7 Code, GLM 5.2, Nemotron Ultra,
DeepSeek V4 Pro, ...) is therefore a catalog refresh + `./dev sync` — config,
never code, and never GPU SKU sizing.

All entries run the SAME image: the llm_app proxy with ENGINE=baseten-api,
whose ModelAPIMux dispatches per-request on `model`. Live when
BASETEN_API_BASE_URL=https://inference.baseten.co (+ BASETEN_API_KEY) is set
on the instance; a faithful per-model sim otherwise (no keys, no network).

Edit the catalog, then `./dev sync`. Stdlib-only: `./dev sync` imports this
module, so declare the image, don't import the app.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "devkit"))

from manifest import Image, service  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
CATALOG = json.loads(
    (REPO / "deploy" / "baseten" / "model-apis.json").read_text())

# The app code is services/llm's llm_app — this manifest is a pool-flavored
# deployment of it (same pattern as services/qwen3_8b), not a fork.
APP = "services/llm"
PATH = "services/model_apis"

image = (
    Image.debian_slim("3.11")
    .workdir("/srv")
    .copy(f"{APP}/requirements.txt", ".")
    .pip_install_requirements("requirements.txt")
    .copy(f"{APP}/llm_app", "./llm_app")
    .copy("deploy/baseten/model-apis.json", "./model-apis.json")
    .run("useradd --create-home --uid 10001 appuser")
    .user("appuser")
    .env(PORT="8080", ENGINE="baseten-api", TARGET="gpu",
         MODEL_NAME="model-apis", MODEL_API_CATALOG="/srv/model-apis.json")
    .expose(8080)
    .healthcheck(
        'python -c "import urllib.request;'
        "urllib.request.urlopen('http://127.0.0.1:8080/healthz')\"",
        interval="10s", timeout="3s", start_period="10s",
    )
    .cmd(["uvicorn", "llm_app.main:app", "--host", "0.0.0.0", "--port", "8080"])
)

# One registry backend per catalog model. Hosted Model APIs are shared
# serverless capacity: effectively always-warm (cold_start_s is network +
# queueing, not weight loading) and scale is Baseten's problem (max_replicas
# here bounds OUR proxy fleet, not their fleet).
SERVICES = [
    service(
        name=m["alias"],
        path=PATH,
        tier="standard",     # chat SLO tier; voice-tier models stay dedicated
        target="gpu",
        engine="baseten-api",
        model_id=m["slug"],
        cold_start_s=0.5,
        kv_ttl_s=300.0,
        max_replicas=2,
        scale_to_zero=False,
        image=image,
    )
    for m in CATALOG["models"]
]
