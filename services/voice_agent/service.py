"""voice-agent — the BYOC demo's migrated route: a voice-workload deployment
of the docs_assist app (short conversational turns, grounded answers).

Voice is the least forgiving serving workload — the repo's voice SLO is
TTFT p99 < 500 ms, TPOT p99 < 60 ms — which is exactly why it anchors the
certified-migration story. Same app as services/docs_assist (this manifest
is a workload-flavored deployment, not a fork); the KB grounding is what
makes its answers certifiable.

Edit THIS file, then `./dev sync`. Stdlib-only: `./dev sync` imports this
module, so declare the image, don't import the app.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "devkit"))

from manifest import Image, service  # noqa: E402

APP = "services/docs_assist"
PATH = "services/voice_agent"

image = (
    Image.debian_slim("3.11")
    .workdir("/srv")
    .copy(f"{APP}/requirements.txt", ".")
    .pip_install_requirements("requirements.txt")
    .copy(f"{APP}/app.py", "./app.py")
    .copy(f"{APP}/retrieval.py", "./retrieval.py")
    .copy(f"{APP}/kb", "./kb")
    .run("useradd --create-home --uid 10001 appuser")
    .user("appuser")
    .env(PORT="8080")
    .expose(8080)
    .healthcheck(
        'python -c "import urllib.request;'
        "urllib.request.urlopen('http://127.0.0.1:8080/healthz')\"",
        interval="10s", timeout="3s", start_period="10s",
    )
    .cmd(["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"])
)

SERVICE = service(
    name="voice-agent",
    path=PATH,
    tier="realtime",         # voice SLO tier: TTFT p99<500ms, TPOT p99<60ms
    target="cpu",            # the agent shim is CPU; GPUs live behind UPSTREAM_BASE_URL
    engine="openai-proxy",
    max_replicas=3,
    scale_to_zero=True,
    image=image,
)
