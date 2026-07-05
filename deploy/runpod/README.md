# RunPod pools — MAX-first, vLLM fallback

Two pods, one model, two vendors. Per-second billing; stop pods when idle.

| Pool | GPU | Serve | Image |
|---|---|---|---|
| `a100-nvidia` | A100 80GB (1x) | `max serve` (fallback: vLLM) | `modular/max-nvidia-full:latest` |
| `mi300x-amd` | MI300X 192GB (1x) | `max serve` (fallback: vLLM ROCm) | `modular/max-amd:latest` |

Model: `Qwen/Qwen2.5-14B-Instruct` (bf16 fits both; use FP8 build on A100
if TTFT is tight). Pin image tags on demo day — check
https://docs.modular.com/max/container for current names, and confirm live
pod pricing in the RunPod console (enter actual $/hr into `./dev bench`).

## 1. Launch (console or API)
Console: Pods -> Deploy -> pick GPU -> use the docker command below as the
container start command -> expose port 8000 -> add HF_TOKEN env if the model
needs it. Or use `launch_pod.sh` with a RunPod API key.

## 2. Serve — MAX (primary path)
    bash serve_max.sh          # prints the exact docker command per vendor

Bring-up discipline (this is part of the story): drive the bring-up with
Modular's own skills (import-model / debug-model) from your coding agent,
and save the transcript — that's the §4.2 flywheel demonstrated.

## 3. Serve — vLLM (tested fallback)
    bash serve_vllm.sh nvidia | amd

## 4. Verify from your laptop
    curl -s http://<POD_IP>:8000/v1/models
    python3 tools/bench.py --base-url http://<POD_IP>:8000/v1 \
      --model Qwen/Qwen2.5-14B-Instruct --pool-usd-hr <ACTUAL> \
      --pool-name a100-nvidia --out bench-reports/a100.json

## Budget guardrail
~20 pod-hours total across build+rehearsal+demo. Stop pods between sessions;
`runpodctl stop pod <id>`.
