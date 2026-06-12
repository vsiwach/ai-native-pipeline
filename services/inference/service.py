"""house-price-reg — resources & image as code.

This is the single source of truth for how this backend is deployed. `./dev
sync` reads it to (re)generate the inference-registry.yaml entry the router
consumes, and can render the Dockerfile below. Edit THIS file, then run
`./dev sync`; never hand-edit the registry for this service.

Kept stdlib-light on purpose: `./dev sync` imports this module, so it must not
import the FastAPI app or model libraries — only declare them.
"""

import sys
from pathlib import Path

# Make the devkit manifest importable whether run via ./dev sync or directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "devkit"))

from manifest import Image, service  # noqa: E402

PATH = "services/inference"

# The container environment, defined by method chaining (Modal-style).
# Mirrors services/inference/Dockerfile — render it with `./dev sync --dockerfiles`.
image = (
    Image.debian_slim("3.11")
    .workdir("/srv")
    .copy(f"{PATH}/requirements.txt", ".")
    .pip_install_requirements("requirements.txt")
    .copy(f"{PATH}/inference_app", "./inference_app")
    .copy(f"{PATH}/sample_model", "./sample_model")
    .copy(f"{PATH}/LICENSE", ".")
    .run("useradd --create-home --uid 10001 appuser")
    .user("appuser")
    .env(PORT="8080")
    .expose(8080)
    .healthcheck(
        'python -c "import urllib.request;'
        "urllib.request.urlopen('http://127.0.0.1:8080/healthz')\"",
        interval="10s", timeout="3s", start_period="15s",
    )
    .cmd(["uvicorn", "inference_app.main:app", "--host", "0.0.0.0", "--port", "8080"])
)

# Runtime resources & scaling policy — the registry entry, as code.
SERVICE = service(
    name="house-price-reg",
    path=PATH,
    tier="standard",      # realtime | standard | batch
    target="cpu",         # cpu | gpu
    max_replicas=3,
    scale_to_zero=True,
    image=image,
)
