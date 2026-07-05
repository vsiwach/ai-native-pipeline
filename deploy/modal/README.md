# Modal — alternate NVIDIA provider

Why: RunPod provisioning has repeatedly rented dead pods (runtime:null —
FRICTION_LOG #16, and BOTH MI300X attempts on 2026-07-05). Modal charges
per-second only while the workload is active and scales to zero on idle,
so it's the natural fallback for the NVIDIA leg of the certified-migration
demo. Modal has no AMD GPUs — the MI300X leg still needs RunPod (or
another AMD cloud) on a healthier day.

    pip install modal                       # ~/.modal.toml already present
    modal deploy deploy/modal/max_serve.py  # -> https://…-serve.modal.run
    curl https://…-serve.modal.run/v1/models

Same pinned image as the pods (`modular/max-nvidia-full:26.4.0`), same
model, so the certification `model_build` string stays comparable. Adopt it
from the console the same way as a pod (the candidate's `/dev/upstream`
takes any OpenAI-compatible base URL); a first-class `provider: modal`
entry in `router_app/gpuops.py` is the natural next step (launch/stop via
`modal` CLI or REST instead of RunPod).

Cost note: A100-80GB on Modal ≈ $2.50/hr while hot, $0 idle — pricier
per active hour than RunPod's $1.39, but a stuck RunPod pod bills for
nothing delivered, which is worse.
