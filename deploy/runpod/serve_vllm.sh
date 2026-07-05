#!/usr/bin/env bash
# vLLM fallback — battle-tested on both vendors.
set -euo pipefail
MODEL="${MODEL:-Qwen/Qwen2.5-14B-Instruct}"
VENDOR="${1:-nvidia}"

if [ "$VENDOR" = "nvidia" ]; then
  echo "docker run --gpus all -p 8000:8000 -e HF_TOKEN=\$HF_TOKEN \\
    vllm/vllm-openai:latest \\
    --model $MODEL --max-model-len 8192"
elif [ "$VENDOR" = "amd" ]; then
  echo "docker run --device=/dev/kfd --device=/dev/dri --group-add video \\
    -p 8000:8000 -e HF_TOKEN=\$HF_TOKEN \\
    rocm/vllm:latest \\
    python -m vllm.entrypoints.openai.api_server --model $MODEL --max-model-len 8192"
else
  echo "usage: serve_vllm.sh nvidia|amd" >&2; exit 1
fi
