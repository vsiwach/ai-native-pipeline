# MAX serving on Modal — alternate NVIDIA provider for the certified-
# migration demo. Modal bills per-second ONLY while the container runs and
# scales to zero when idle, so a flaky-RunPod day costs nothing extra.
# (Modal is NVIDIA-only — the AMD/MI300X leg still needs RunPod or another
# cloud.)
#
#   pip install modal          # credentials already in ~/.modal.toml
#   modal deploy deploy/modal/max_serve.py
#   -> https://<workspace>--max-qwen25-serve.modal.run/v1/models
#
# Point the console's candidate at it exactly like a pod:
#   POST /dev/upstream {"base_url": "https://...modal.run/v1",
#                       "model": "Qwen/Qwen2.5-14B-Instruct"}
# The gpuops surface can grow a "modal" provider next; for now this app is
# launched with the modal CLI (deploy) and torn down with `modal app stop`.

import modal

MODEL = "Qwen/Qwen2.5-14B-Instruct"
PORT = 8000

# Same pinned MAX container the RunPod pods run — identical build string in
# the certification record. add_python bolts Modal's client onto the image.
image = modal.Image.from_registry(
    "modular/max-nvidia-full:26.4.0", add_python="3.11"
).entrypoint([])

app = modal.App("max-qwen25")


@app.function(
    image=image,
    gpu="A100-80GB",
    timeout=60 * 60,
    scaledown_window=120,     # idle 2 min -> scale to zero -> $0
)
@modal.concurrent(max_inputs=32)
@modal.web_server(PORT, startup_timeout=15 * 60)
def serve():
    import subprocess
    subprocess.Popen(
        ["max", "serve", "--model-path", MODEL, "--port", str(PORT)])
