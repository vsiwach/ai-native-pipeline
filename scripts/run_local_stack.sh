#!/usr/bin/env bash
# One-command workload deploy (local, $0): two qwen3-8b pools + router +
# devboard + incident agent. Sim by default; export BASETEN_BASE_URL /
# VLLM_BASE_URL (+ keys) before running to point the same stack at live
# pools. Ctrl-C tears everything down.
#
#   ./scripts/run_local_stack.sh [router_port] [--load]
#
# Then open  http://localhost:${ROUTER_PORT:-8090}/devboard
set -euo pipefail
cd "$(dirname "$0")/.."
ROUTER_PORT="${1:-8090}"
BASETEN_PORT=8101
VLLM_PORT=8102
MODEL_API_A_PORT=8103
MODEL_API_B_PORT=8104
WORK="$(mktemp -d)"
trap 'kill 0 2>/dev/null' EXIT INT TERM

# routing policy with localhost pool URLs (repo policy uses compose hostnames)
sed "s|http://pool-baseten:8080|http://127.0.0.1:${BASETEN_PORT}|; \
     s|http://pool-vllm:8080|http://127.0.0.1:${VLLM_PORT}|; \
     s|http://pool-model-api-a:8080|http://127.0.0.1:${MODEL_API_A_PORT}|; \
     s|http://pool-model-api-b:8080|http://127.0.0.1:${MODEL_API_B_PORT}|" \
    routing-policy.yaml > "$WORK/routing-policy.yaml"

echo "· pool baseten-l4 (sim unless BASETEN_BASE_URL set) :${BASETEN_PORT}"
(cd services/llm && CHAOS_ENABLED=1 ENGINE=baseten MODEL_NAME=qwen3-8b \
  DECODE_MS_PER_TOKEN=28 COLD_START_S=45 USD_PER_1M_COMPLETION=1.05 \
  BASETEN_BASE_URL="${BASETEN_BASE_URL:-}" POOL_USD_PER_HOUR="${BASETEN_USD_PER_HOUR:-1.05}" \
  python3 -m uvicorn llm_app.main:app --host 127.0.0.1 \
  --port "$BASETEN_PORT" --log-level error) &

echo "· pool vllm-l4    (sim unless VLLM_BASE_URL set)    :${VLLM_PORT}"
(cd services/llm && CHAOS_ENABLED=1 ENGINE=vllm MODEL_NAME=qwen3-8b \
  DECODE_MS_PER_TOKEN=24 COLD_START_S=120 USD_PER_1M_COMPLETION=0.60 \
  VLLM_BASE_URL="${VLLM_BASE_URL:-}" POOL_USD_PER_HOUR="${VLLM_USD_PER_HOUR:-0.60}" \
  python3 -m uvicorn llm_app.main:app --host 127.0.0.1 \
  --port "$VLLM_PORT" --log-level error) &

# Baseten hosted Model APIs — one mux proxy serves the whole catalog
# (deploy/baseten/model-apis.json). Two replicas so quarantine can spill.
# Live upstream when BASETEN_API_BASE_URL is exported (needs BASETEN_API_KEY),
# e.g.  export BASETEN_API_BASE_URL=https://inference.baseten.co
for P in "a:${MODEL_API_A_PORT}" "b:${MODEL_API_B_PORT}"; do
  SUFFIX="${P%%:*}"; PORT="${P##*:}"
  echo "· pool model-api-${SUFFIX} (sim unless BASETEN_API_BASE_URL set) :${PORT}"
  (cd services/llm && CHAOS_ENABLED=1 ENGINE=baseten-api MODEL_NAME=model-apis \
    BASETEN_API_BASE_URL="${BASETEN_API_BASE_URL:-}" \
    MODEL_API_DEFAULT="${MODEL_API_DEFAULT:-}" \
    python3 -m uvicorn llm_app.main:app --host 127.0.0.1 \
    --port "$PORT" --log-level error) &
done

sleep 1
echo "· router + devboard + incident agent                :${ROUTER_PORT}"
(cd services/router && \
  ROUTING_POLICY_PATH="$WORK/routing-policy.yaml" \
  GOODPUT_CURVES_PATH="$PWD/benchmarks/goodput.json" \
  ROUTER_QUEUE_DIR="$WORK/queue" HEALTH_POLL_INTERVAL_S=2 \
  python3 -m uvicorn router_app.main:app --host 127.0.0.1 \
  --port "$ROUTER_PORT" --log-level error) &

sleep 2
echo
echo "devboard:  http://localhost:${ROUTER_PORT}/devboard"
echo "drill:     python3 tools/chaos.py inject --target http://localhost:${VLLM_PORT} --latency-ms 600"
echo "           (the incident agent quarantines, probes, reinstates, resolves)"

if [[ "${2:-}" == "--load" ]]; then
  echo "· steady load (bench harness, c=4, until Ctrl-C)"
  while true; do
    python3 benchmarks/harness.py --router "http://localhost:${ROUTER_PORT}" \
      --model qwen3-8b --concurrency 4 --duration 60 \
      --label stack-load --out-dir "$WORK/load" >/dev/null
  done &
fi
wait
