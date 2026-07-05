#!/usr/bin/env bash
# Phase 6 certified-migration loop, fully local, no GPU, no keys:
#   llm-sim <- docs-assist(primary) + docs-assist(candidate)
#   router mirrors primary traffic to the candidate (shadow)
#   replay -> shadow log -> bench -> certify (signed) -> verify -> tamper test
#   + promote/rollback drill through the release endpoints
# Artifacts land in demo-artifacts/<UTC-stamp>/.
#
# Own-PID cleanup only (run_local_stack.sh's `kill 0` murders parent
# scripts — see docs/KNOWN_ISSUES.md).
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_DIR="$REPO/demo-artifacts/$STAMP"
mkdir -p "$RUN_DIR"

KB="$REPO/services/docs_assist/kb/modular_kb.sqlite"
[ -f "$KB" ] || { echo "KB index missing — run tools/ragindex/build_index.py first"; exit 1; }

PORT_SIM=8111 PORT_PRIMARY=8112 PORT_CANDIDATE=8113 PORT_ROUTER=8114
for p in $PORT_SIM $PORT_PRIMARY $PORT_CANDIDATE $PORT_ROUTER; do
  if lsof -ti ":$p" >/dev/null 2>&1; then
    echo "port $p is busy (a previous run leaked?) — kill it first:"
    echo "  lsof -ti :$PORT_SIM -ti :$PORT_PRIMARY -ti :$PORT_CANDIDATE -ti :$PORT_ROUTER | xargs kill"
    exit 1
  fi
done
# exec inside the subshell so $! IS the server pid (a plain subshell pid
# would die on kill while the python child lived on, leaking ports)
PIDS=()
cleanup() { for p in "${PIDS[@]:-}"; do kill "$p" 2>/dev/null || true; done; }
trap cleanup EXIT

wait_healthy() { # url
  for _ in $(seq 1 60); do
    curl -sf "$1/healthz" >/dev/null 2>&1 && return 0
    sleep 0.5
  done
  echo "never healthy: $1"; exit 1
}

echo "== starting llm-sim (:$PORT_SIM)"
(cd services/llm && exec env ENGINE=max TARGET=cpu MODEL_NAME=llm-sim COLD_START_S=1.0 \
  python3 -m uvicorn llm_app.main:app --port $PORT_SIM --log-level warning \
  >"$RUN_DIR/llm-sim.log" 2>&1) & PIDS+=($!)

echo "== starting docs-assist primary (:$PORT_PRIMARY) + candidate (:$PORT_CANDIDATE)"
for role_port in "primary:$PORT_PRIMARY" "candidate:$PORT_CANDIDATE"; do
  role="${role_port%%:*}"; port="${role_port##*:}"
  (cd services/docs_assist && exec env \
    UPSTREAM_BASE_URL="http://127.0.0.1:$PORT_SIM/v1" UPSTREAM_MODEL=llm-sim \
    KB_INDEX="$KB" \
    python3 -m uvicorn app:app --port "$port" --log-level warning \
    >"$RUN_DIR/docs-assist-$role.log" 2>&1) & PIDS+=($!)
done

echo "== writing loop policy + starting router (:$PORT_ROUTER)"
POLICY="$RUN_DIR/routing-policy.loop.yaml"
cat >"$POLICY" <<EOF
tiers:
  realtime: {max_latency_ms: 30000, prefer: lowest_latency, ttft_ms: 5000, tpot_ms: 200}
  standard: {max_latency_ms: 30000, prefer: lowest_cost}
  batch: {max_latency_ms: null, prefer: lowest_cost, queue: true}
cost_table: {frontier-api: 10.0, shadow-candidate: 0.5}
cache: {enabled: false}
affinity: {enabled: false, prefix_tokens: 32, capacity: 8}
routes:
  docs-assist:
    shadow_candidate: http://127.0.0.1:$PORT_CANDIDATE/v1
    shadow_id: docs-assist-candidate
    shadow_provider: shadow-candidate
endpoints:
  docs-assist:
    - {id: frontier, provider: frontier-api, url: "http://127.0.0.1:$PORT_PRIMARY"}
EOF
(cd services/router && exec env \
  REGISTRY_PATH="$REPO/inference-registry.yaml" ROUTING_POLICY_PATH="$POLICY" \
  SHADOW_LOG_DIR="$RUN_DIR/shadow-logs" ROUTER_QUEUE_DIR="$RUN_DIR/queue" \
  BENCH_REPORTS_DIR="$RUN_DIR/bench-reports" INCIDENT_AGENT=0 \
  python3 -m uvicorn router_app.main:app --port $PORT_ROUTER --log-level warning \
  >"$RUN_DIR/router.log" 2>&1) & PIDS+=($!)

wait_healthy "http://127.0.0.1:$PORT_SIM"
wait_healthy "http://127.0.0.1:$PORT_PRIMARY"
wait_healthy "http://127.0.0.1:$PORT_CANDIDATE"
wait_healthy "http://127.0.0.1:$PORT_ROUTER"
echo "== all healthy"

echo "== replaying evals through the router (shadow fills)"
python3 tools/replay.py --router "http://127.0.0.1:$PORT_ROUTER" \
  --route docs-assist --evals evals/docs_qa.jsonl --rps 2 --loop 1 \
  | tee "$RUN_DIR/replay.log"

echo "== waiting for the shadow mirror to drain"
SHADOW_LOG="$RUN_DIR/shadow-logs/docs-assist.shadow.jsonl"
N_EVALS=$(grep -c . evals/docs_qa.jsonl)
for _ in $(seq 1 60); do
  n=$(grep -c . "$SHADOW_LOG" 2>/dev/null || echo 0)
  [ "$n" -ge "$N_EVALS" ] && break
  sleep 0.5
done
[ -f "$SHADOW_LOG" ] || { echo "shadow log never appeared: $SHADOW_LOG"; exit 1; }
echo "   shadow log lines: $(grep -c . "$SHADOW_LOG")"

echo "== shadow-stats + /v1/costs snapshots"
curl -s "http://127.0.0.1:$PORT_ROUTER/v1/routes/docs-assist/shadow-stats" \
  | tee "$RUN_DIR/shadow-stats.json"; echo
curl -s "http://127.0.0.1:$PORT_ROUTER/v1/costs" >"$RUN_DIR/costs.before-promote.json"

echo "== bench: candidate pool through its OpenAI surface (sim; declared \$0/hr)"
./dev bench --base-url "http://127.0.0.1:$PORT_CANDIDATE/v1" --model llm-sim \
  --pool-usd-hr 0.0 --pool-name llm-sim-local --profile docs-agent \
  --requests 12 --concurrency 3 --slo-ttft-ms 5000 \
  --out "$RUN_DIR/bench-reports/llm-sim-local.json" | tee "$RUN_DIR/bench.log"

echo "== certify (real gate 0.90 — expected HOLD against the lorem sim)"
set +e
python3 tools/certify.py run --evals evals/docs_qa.jsonl \
  --shadow-log "$SHADOW_LOG" \
  --bench-report "$RUN_DIR/bench-reports/llm-sim-local.json" \
  --route-config "$POLICY" --model-build "llm-sim@max-local-sim" \
  --gate-parity 0.90 --slo-ttft-ms 5000 --out "$RUN_DIR/certs-gate90" \
  | tee "$RUN_DIR/certify-gate90.log"
echo "   exit=$? (2 = HOLD, expected: the sim emits no [n] citations)"
set -e

echo "== certify smoke (gate 0 — pipeline-plumbing cert; gate shown in record)"
./dev certify run --evals evals/docs_qa.jsonl \
  --shadow-log "$SHADOW_LOG" \
  --bench-report "$RUN_DIR/bench-reports/llm-sim-local.json" \
  --route-config "$POLICY" --model-build "llm-sim@max-local-sim" \
  --gate-parity 0.0 --slo-ttft-ms 5000 --out "$RUN_DIR/certs" \
  | tee "$RUN_DIR/certify-smoke.log"

CERT=$(ls -t "$RUN_DIR/certs/"*.cert.json | head -1)
echo "== verify: $CERT"
python3 tools/certify.py verify "$CERT" | tee "$RUN_DIR/verify.log"

echo "== tamper test (parity 0.90 gate cert also present in certs-gate90/)"
TAMPERED="$RUN_DIR/tampered.cert.json"
python3 - "$CERT" "$TAMPERED" <<'PY'
import json, sys
rec = json.loads(open(sys.argv[1]).read())
rec["quality"]["parity"] = 1.0          # forge a perfect score
open(sys.argv[2], "w").write(json.dumps(rec, indent=2))
PY
set +e
python3 tools/certify.py verify "$TAMPERED" | tee "$RUN_DIR/tamper.log"
TAMPER_EXIT=$?
set -e
[ "$TAMPER_EXIT" -ne 0 ] || { echo "TAMPER TEST FAILED: forged cert verified"; exit 1; }
echo "   tampered cert rejected (exit $TAMPER_EXIT) — signature binds the scores"

echo "== promote/rollback drill through the release endpoints"
curl -s -X POST "http://127.0.0.1:$PORT_ROUTER/v1/routes/docs-assist/promote" \
  | tee "$RUN_DIR/promote.json"; echo
curl -s "http://127.0.0.1:$PORT_ROUTER/v1/chat/completions?model=docs-assist" \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"What is Mammoth?"}],"max_tokens":32}' \
  -D "$RUN_DIR/chat-after-promote.headers" -o "$RUN_DIR/chat-after-promote.json"
grep -i x-replica "$RUN_DIR/chat-after-promote.headers"
curl -s -X POST "http://127.0.0.1:$PORT_ROUTER/v1/routes/docs-assist/rollback" \
  | tee "$RUN_DIR/rollback.json"; echo
curl -s "http://127.0.0.1:$PORT_ROUTER/v1/costs" >"$RUN_DIR/costs.final.json"
curl -s "http://127.0.0.1:$PORT_ROUTER/v1/events?limit=200" >"$RUN_DIR/events.json"

echo "== done — artifacts in $RUN_DIR"
