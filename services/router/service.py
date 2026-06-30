"""router — resources & image as code.

The router is infrastructure (section="services"): CI builds and smoke-tests
it like any backend, but it is never a routing target itself. Its registry
entry lives in the hand-maintained `services:` section of
inference-registry.yaml, which `./dev sync` preserves verbatim.

Kept stdlib-light on purpose: `./dev sync` imports this module, so it must not
import the FastAPI app — only declare it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "devkit"))

from manifest import Image, service  # noqa: E402

PATH = "services/router"

# Mirrors services/router/Dockerfile — render with `./dev sync --dockerfiles`.
image = (
    Image.debian_slim("3.11")
    .workdir("/srv")
    .copy(f"{PATH}/requirements.txt", ".")
    .pip_install_requirements("requirements.txt")
    .copy(f"{PATH}/router_app", "./router_app")
    .copy("inference-registry.yaml", ".")
    .copy("routing-policy.yaml", ".")
    .copy("placement-policy.yaml", ".")
    .run("useradd --create-home --uid 10001 appuser")
    .user("appuser")
    .env(PORT="8080", REGISTRY_PATH="/srv/inference-registry.yaml",
         ROUTING_POLICY_PATH="/srv/routing-policy.yaml",
         PLACEMENT_POLICY_PATH="/srv/placement-policy.yaml")
    .expose(8080)
    .healthcheck(
        'python -c "import urllib.request;'
        "urllib.request.urlopen('http://127.0.0.1:8080/healthz')\"",
        interval="10s", timeout="3s", start_period="10s",
    )
    .cmd(["uvicorn", "router_app.main:app", "--host", "0.0.0.0",
          "--port", "8080"])
)

SERVICE = service(
    name="router",
    path=PATH,
    tier="realtime",
    target="cpu",
    max_replicas=3,
    scale_to_zero=False,
    image=image,
    section="services",
)
