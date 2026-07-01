# RunPod vLLM pool (second pool)

One self-hosted pod (L4 or A10, ~$0.30-0.60/hr) running the official
`vllm/vllm-openai` image with the same Qwen3-8B-class model as the Baseten
pool. This is the pool we fully control — chaos drills kill THIS one.

## Files
- `pod.py` — provision (`up`), `status`, teardown (`down`), `budget`.
  `RUNPOD_API_KEY` env var only; `up`/`down` require `--yes`.
- `spend-ledger.json` — committed record of every billable hour (created on
  first `up`). `pod.py up` ABORTS if projected spend exceeds the $40 mission
  cap. `.pod-state.json` (gitignored) pins the single live pod id.

## Live session checklist
1. `export RUNPOD_API_KEY=...` (+ `HF_TOKEN` if the model needs it)
2. `python3 deploy/runpod/pod.py up --yes` → wait for RUNNING in `status`
3. Smoke: `curl https://<pod-id>-8000.proxy.runpod.net/v1/models`
4. Wire the URL into the router registry (VllmAdapter `base_url`)
5. ALWAYS `python3 deploy/runpod/pod.py down --yes` at session end — the
   ledger keeps counting until the entry closes.

REST paths were written from docs knowledge — verify on first live run; every
mismatch is a docs/FRICTION_LOG.md entry.
