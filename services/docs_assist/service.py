"""docs-assist — retrieval-grounded docs agent, the certified-migration route.

The service is a CPU-side OpenAI-compatible proxy (engine=openai-proxy):
retrieval + grounding happen here, generation happens at whatever
UPSTREAM_BASE_URL points to (MAX / vLLM pod, frontier API, or llm-sim).
The KB index and retrieval never leave the service (in-VPC egress by
design — the GPU pool only ever sees the grounded prompt).

Edit THIS file, then `./dev sync`. Stdlib-only: `./dev sync` imports this
module, so declare the image, don't import the app.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "devkit"))

from manifest import Image, service  # noqa: E402

PATH = "services/docs_assist"

image = (
    Image.debian_slim("3.11")
    .workdir("/srv")
    .copy(f"{PATH}/requirements.txt", ".")
    .pip_install_requirements("requirements.txt")
    .copy(f"{PATH}/app.py", "./app.py")
    .copy(f"{PATH}/retrieval.py", "./retrieval.py")
    .copy(f"{PATH}/kb", "./kb")
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
    name="docs-assist",
    path=PATH,
    tier="realtime",
    target="cpu",            # the agent shim is CPU; GPUs live behind UPSTREAM_BASE_URL
    engine="openai-proxy",
    max_replicas=3,
    scale_to_zero=True,
    image=image,
)
