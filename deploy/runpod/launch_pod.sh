#!/usr/bin/env bash
# Launch a RunPod pod via REST API. Requires RUNPOD_API_KEY.
# usage: launch_pod.sh a100|mi300x
set -euo pipefail
KIND="${1:?usage: launch_pod.sh a100|mi300x}"
case "$KIND" in
  a100)   GPU="NVIDIA A100 80GB PCIe"; IMAGE="modular/max-nvidia-full:latest";;
  mi300x) GPU="AMD Instinct MI300X OAM"; IMAGE="modular/max-amd:latest";;
  *) echo "unknown kind"; exit 1;;
esac
curl -s -X POST "https://rest.runpod.io/v1/pods" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY:?set RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"modular-demo-$KIND\",
    \"imageName\": \"$IMAGE\",
    \"gpuTypeIds\": [\"$GPU\"],
    \"gpuCount\": 1,
    \"containerDiskInGb\": 80,
    \"ports\": [\"8000/http\"],
    \"env\": {\"HF_TOKEN\": \"${HF_TOKEN:-}\"}
  }" | python3 -m json.tool
# NOTE: verify gpuTypeIds against GET /v1/gpus — names drift.
