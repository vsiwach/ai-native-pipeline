#!/usr/bin/env bash
# MAX serving commands per vendor. Run ON the pod (or paste as the pod's
# docker command). Check docs.modular.com/max/container for current tags.
set -euo pipefail
MODEL="${MODEL:-Qwen/Qwen2.5-14B-Instruct}"
VENDOR="${1:-nvidia}"

if [ "$VENDOR" = "nvidia" ]; then
  echo "docker run --gpus all -p 8000:8000 -e HF_TOKEN=\$HF_TOKEN \\
    modular/max-nvidia-full:latest \\
    max serve --model-path $MODEL --port 8000"
elif [ "$VENDOR" = "amd" ]; then
  echo "docker run --device=/dev/kfd --device=/dev/dri --group-add video \\
    -p 8000:8000 -e HF_TOKEN=\$HF_TOKEN \\
    modular/max-amd:latest \\
    max serve --model-path $MODEL --port 8000"
else
  echo "usage: serve_max.sh nvidia|amd" >&2; exit 1
fi
echo
echo "# smoke: curl -s localhost:8000/v1/models"
echo "# if MAX bring-up stalls on MI300X, fall back: bash serve_vllm.sh amd"
