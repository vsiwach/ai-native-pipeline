# Live Baseten deployment — qwen3-8b-pool

First live deploy: 2026-07-02 (F1 primary pool).

| field | value |
|---|---|
| model name | qwen3-8b-pool |
| model id | `qrj78jv3` |
| deployment id | `wno2dv0` |
| endpoint base | `https://model-qrj78jv3.api.baseten.co` |
| logs | https://app.baseten.co/models/qrj78jv3/logs/wno2dv0 |
| instance | L4:2x24x96 (2× L4, 48GiB VRAM) — note: 2× not 1× |
| autoscaling | min 0 / max 1 · concurrency 8 · scale_down_delay 900s |

## Cost control
- min_replica 0 → idle cost \$0; but a 900s (15 min) idle tail bills after
  each use before scale-down. `python3 deploy/baseten/manage.py deactivate
  wno2dv0 --model-id qrj78jv3 --yes` when done for the day.
- Covered by workspace free credits for now; \$40 mission guard is backstop.

## Invocation (VERIFY LIVE — custom Truss model.py)
A custom `model.py` is invoked via Baseten's predict path, NOT a raw
OpenAI `/v1/chat/completions`. Expected:
`POST {base}/environments/production/predict` with the chat request as body,
`Authorization: Api-Key $BASETEN_API_KEY`, returning the OpenAI-shaped dict
our `model.py` builds. The BasetenAdapter is wired for OpenAI streaming and
will likely need a Baseten-predict mode — confirm the actual path once the
replica is ACTIVE, then adjust the adapter + routing-policy URL.
