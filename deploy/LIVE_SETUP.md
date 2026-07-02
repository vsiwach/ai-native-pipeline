# Live cross-cloud setup — working configs + reactivation runbook

Captured 2026-07-02 after the dedicated Baseten pool first went live.
Everything here WORKED; costs listed so nothing is left running by accident.

## Pool 1 — Baseten dedicated (custom vLLM Truss) ✅ proven live
- Model `qwen3-8b-vllm` (id `3ydn1e43`), deployment `w52yvzr`, instance
  `T4x8x32` ($0.01504/min ≈ $0.90/hr while a replica is up)
- Truss: [baseten/vllm-truss/](baseten/vllm-truss/) — the exact working
  config: `instance_type: T4x8x32`, `vllm==0.9.1` **with
  `transformers==4.53.2` pinned** (unpinned = aimv2 import crash),
  `Qwen/Qwen3-8B-AWQ`, fp16, `MAX_MODEL_LEN=4096`
- Measured warm: TTFT ~330ms, TPOT ~34ms/tok (inside voice SLO)
- Wire into the stack:
  ```bash
  export BASETEN_BASE_URL=https://model-3ydn1e43.api.baseten.co/environments/production
  export BASETEN_CHAT_PATH=/predict     # custom truss serves /predict
  export BASETEN_USD_PER_HOUR=0.90
  ```
- Reactivate after shutdown (build is kept; cold start ≈ 6 min model load):
  ```bash
  python3 deploy/baseten/manage.py activate w52yvzr --model-id 3ydn1e43 --yes
  # if production ever points at a dead deployment again (friction #15):
  python3 deploy/baseten/manage.py promote  w52yvzr --model-id 3ydn1e43 --yes
  ```
- Shutdown: `python3 deploy/baseten/manage.py deactivate w52yvzr --model-id 3ydn1e43 --yes`

## Pool 2 — Baseten Model APIs (serverless, per-token) ✅ proven live
- Nothing to activate or shut down — billed per token only.
- Catalog: [baseten/model-apis.json](baseten/model-apis.json) (11 models);
  refresh with `python3 deploy/baseten/manage.py catalog --fetched-at <iso>`
- Wire: `export BASETEN_API_BASE_URL=https://inference.baseten.co`
- Caution: per-model rate limits, no Retry-After (FRICTION #10) — keep drill
  load ≤0.5 rps live.

## Pool 3 — RunPod vLLM pod ✅ proven live 2026-07-01 (capacity-flaky 07-02)
- `python3 deploy/runpod/pod.py up --est-hours N --yes` (budget-guarded,
  ledger-committed). vLLM image, Qwen/Qwen3-8B, ~$0.4–0.7/hr.
- Wire: `export VLLM_BASE_URL=https://<pod-id>-8000.proxy.runpod.net`
  (`VLLM_USD_PER_HOUR` to match the pod's rate)
- 2026-07-02: three consecutive 4090/A5000 pods stuck "rented, runtime:null"
  (billing while dead) — check `pod.py status` shows a `runtime` object
  within ~10 min or kill it.
- Shutdown: `python3 deploy/runpod/pod.py down --yes` (closes spend ledger)

## Full live stack (router + devboard + incident agent)
```bash
export DEVBOARD_MODEL=qwen3-8b        # the model the agent watches
# + pool exports above (any subset; missing pools run as faithful sims)
./scripts/run_local_stack.sh 8096
# devboard: http://localhost:8096/devboard
# drills:   python3 tools/chaos.py drill --suite --model qwen3-8b --rps 2
```

## Shutdown checklist (nothing left billing)
1. `python3 deploy/runpod/pod.py down --yes` → ledger entry closed
2. `python3 deploy/baseten/manage.py deactivate w52yvzr --model-id 3ydn1e43 --yes`
3. H100 experiment (`qjj05vj`, model `qrj78jv3`): deactivate if it ever
   finishes building; builds themselves don't bill replicas.
4. Verify: `manage.py status` shows 0 active replicas everywhere;
   `pod.py status` shows no pod; Baseten billing page "dedicated" flat.
