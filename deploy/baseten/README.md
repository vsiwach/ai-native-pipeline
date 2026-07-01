# Baseten pool (primary) — Truss deploy + management

The mission's primary pool: a Qwen3-8B-class model served OpenAI-compatible
via vLLM inside a Truss, deployed with `truss push`, managed via the Baseten
management API.

## Files
- `config.yaml` + `model/model.py` — the Truss (config.yml/model.py idioms).
  Both pools run the same model for a fair F1 baseline (see DESIGN.md
  deviations log 2026-07-01).
- `manage.py` — status / autoscaling / activate / deactivate / promote / logs
  against the management API. `BASETEN_API_KEY` env var only; mutating calls
  require `--yes`.

## Live session checklist (nothing below runs without keys)
1. `pip install truss` (deploy tooling only — not a Bazel/service dep)
2. `export BASETEN_API_KEY=...`
3. `cd deploy/baseten && truss push --publish`
4. `python3 deploy/baseten/manage.py status` → note model id + deployment id
5. Set autoscaling for F2: `manage.py autoscaling <dep> --model-id <id> \
   --min 0 --max 3 --concurrency 8 --yes` (scale-to-zero = min 0)
6. Wire the deployment URL into the router registry (BasetenAdapter `base_url`)

API paths in `manage.py` and Truss field names in `config.yaml` were written
from docs knowledge — smoke-test on first contact and log every mismatch to
docs/FRICTION_LOG.md (that's the PM artifact).

Budget: Baseten spend counts toward the $40 mission cap. Prefer scale-to-zero
between sessions; `manage.py deactivate` when idle for days.
