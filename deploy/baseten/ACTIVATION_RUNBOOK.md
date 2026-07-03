# ACTIVATION RUNBOOK — qwen3-8b-vllm (model `3ydn1e43`, deployment `w52yvzr`)

Operator runbook for reactivating the custom-Truss vLLM deployment (T4x8x32,
`Qwen/Qwen3-8B-AWQ`), gating readiness, serving via
`/environments/production/predict`, and parking it again. Every claim cites a
docs.baseten.co page from the local snapshot (`tools/kb/baseten`, fetched
2026-07-02). Where the docs are silent, that is said explicitly.

All commands assume `BASETEN_API_KEY` is set. Local CLI:
`python3 deploy/baseten/manage.py` (wraps the management API below).
**Human executes anything that spends money (activate, min_replica > 0).**

---

## Step 1 — Activate

```sh
python3 deploy/baseten/manage.py activate w52yvzr --model-id 3ydn1e43 --yes
# equivalent raw API:
curl -X POST https://api.baseten.co/v1/models/3ydn1e43/deployments/w52yvzr/activate \
  -H "Authorization: Bearer $BASETEN_API_KEY"
```

- Endpoint: `POST /v1/models/{model_id}/deployments/{deployment_id}/activate` —
  "Activates an inactive deployment and returns the activation status."
  Source: https://docs.baseten.co/reference/management-api/deployments/activate/activates-a-deployment
  (full endpoint table: https://docs.baseten.co/reference/management-api/overview)
- CLI equivalent: `baseten model deployment activate --model-id <id> --deployment-id <id>`;
  JSON payload is `managementapi.ActivateResponse` (`--jq '.success'`).
  Source: https://docs.baseten.co/reference/cli/baseten/model-deployment

**States you will see.** The documented deployment statuses are:
*Inactive* → (activate) → *Starting up* → *Active* / *Scaled to zero*, with
error states *Unhealthy*, *Build failed*, *Deployment failed*.
Source: https://docs.baseten.co/observability/health

**When billing starts.** "Baseten meters usage by the minute. For every minute
a replica is observed as up on a node, the per-minute price for its instance
type applies." Cold start is billed: "Model load happens after the replica is
observed as up but before it is healthy enough to serve, so those minutes are
on the bill." Image pull onto the node is NOT billed; a failed boot ("replica
was never observed as up") is NOT billed.
Source: https://docs.baseten.co/organization/billing

## Step 2 — Readiness gate (do this BEFORE routing traffic)

There is no single documented "wait-for-ready" call; the documented building
blocks are status polling + wake:

1. **Poll status** until `ACTIVE`:
   ```sh
   python3 deploy/baseten/manage.py status --model-id 3ydn1e43
   # raw: GET /v1/models/3ydn1e43/deployments/w52yvzr
   # CLI: baseten model deployment describe --model-id 3ydn1e43 --deployment-id w52yvzr --jq '.status'
   ```
   Sources: https://docs.baseten.co/reference/management-api/deployments/gets-a-models-deployment-by-id ,
   https://docs.baseten.co/reference/cli/baseten/model-deployment (`describe ... --jq '.status'`),
   status vocabulary: https://docs.baseten.co/observability/health

2. **Wake without sending a real request** (documented wake endpoints on the
   inference API, 600 s server-side timeout on `/wake`):
   ```sh
   curl -X POST https://model-3ydn1e43.api.baseten.co/production/wake \
     -H "Authorization: Bearer $BASETEN_API_KEY"
   # or per-deployment: POST .../deployment/w52yvzr/wake
   ```
   Source: https://docs.baseten.co/reference/inference-api/overview (Wake
   endpoints table; "Wake (`/wake`) — 600 seconds (10 minutes)" timeout)

3. **Understand what "ready" means internally.** The startup probe passes only
   when "`load()` finishes and the optional `is_healthy()` check passes"; all
   readiness/liveness probes are delayed until then. Startup phase default is
   30 min (`startup_threshold_seconds`, max 3000 s). The readiness probe then
   controls whether the replica receives traffic at all.
   Source: https://docs.baseten.co/development/model/health-checks

4. **Synthetic probe**: send one cheap prompt to
   `POST https://model-3ydn1e43.api.baseten.co/environments/production/predict`
   and require a 200 before opening real traffic. (Endpoint path:
   https://docs.baseten.co/reference/inference-api/overview )

### About the 500 "Model is unhealthy, it is not ready to make predictions"

- That exact error string is **not documented** anywhere in the docs corpus
  (verified against the full snapshot). The closest documented behaviors:
  - A sync request that arrives with no ready replica is **parked**, and "If no
    replica becomes available before the predict timeout ... expires, the
    parked request fails with a `500`." And: "A `500` from a sync request
    during a cold start can mean the parking timeout expired before a replica
    finished starting. Retrying after a brief wait of 30 seconds to a minute
    often succeeds once the replica is ready."
    Source: https://docs.baseten.co/deployment/autoscaling/request-lifecycle
  - The *Unhealthy* status: "The deployment is active but is in an unhealthy
    state due to errors while running... You can try deactivating and
    reactivating your deployment to see if the issue goes away."
    Source: https://docs.baseten.co/observability/health
- So: 500s during load are consistent with documented parking-timeout behavior;
  the recommended documented posture is retry-after-30-60 s plus keeping
  `min_replica` above zero for latency-sensitive traffic. **But also check
  friction #15 below — in our history this exact string was produced by the
  production environment pointing at a dead deployment, not by warming.**
- Note a docs inconsistency: the request-lifecycle page says the predict/parking
  timeout default is "600 seconds" in prose but "1200 seconds" in its status
  table, and the inference API reference says sync predict is 1200 s. Assume
  1200 s for `/predict`, but don't rely on the parked window being that long.
  Sources: https://docs.baseten.co/deployment/autoscaling/request-lifecycle ,
  https://docs.baseten.co/reference/inference-api/overview

## Step 3 — Serve production traffic

- Endpoint: `POST https://model-3ydn1e43.api.baseten.co/environments/production/predict`
  (equivalently `/production/predict`). Deployment-scoped canary:
  `/deployment/w52yvzr/predict`.
  Source: https://docs.baseten.co/reference/inference-api/overview
- The routing layer retries replica-level `502/503/504` automatically with
  exponential backoff (500 ms × 1.5, cap 60 s; connection failures capped at 16
  attempts); check `X-BASETEN-MODEL-PREDICTION-ATTEMPTS` when diagnosing
  latency spikes.
  Source: https://docs.baseten.co/deployment/autoscaling/request-lifecycle
- Concurrency: "Concurrency target should be less than or equal to
  predict_concurrency." Our Truss sets `predict_concurrency: 4`
  (`deploy/baseten/vllm-truss/config.yaml`), so keep `concurrency_target ≤ 4`
  despite the generic vLLM guidance of 32–128.
  Source: https://docs.baseten.co/deployment/autoscaling/overview

### Cold-start mitigations that apply to this vLLM custom Truss

Contributing factors are documented as container pull + weight load + engine
initialization; "engine initialization... dominates for small models (a few
billion parameters or fewer), where CUDA graph capture and `torch.compile` can
run well over a minute, and Baseten doesn't cache those artifacts unless you
opt in."
Source: https://docs.baseten.co/deployment/autoscaling/cold-starts

1. **BDN cached weights (not currently enabled here).** Our Truss downloads
   `Qwen/Qwen3-8B-AWQ` at `load()` time via the `MODEL_ID` env var — there is
   no `weights:` block, so every cold start re-downloads from Hugging Face.
   Docs: "BDN runs automatically on engine-builder deployments. On any other
   deployment, turn it on by adding a `weights` block to your config"; with a
   `weights` block, "Weights are fetched during `truss push` and cached, so
   cold starts only read from local or nearby caches." Pin a commit SHA
   (`hf://Qwen/Qwen3-8B-AWQ@<sha>`) and point vLLM at the `mount_location`.
   (`model_cache` is deprecated in favor of `weights`.)
   Sources: https://docs.baseten.co/deployment/autoscaling/cold-starts ,
   https://docs.baseten.co/development/model/bdn
2. **Torch-compile / runtime caching (b10cache).** "Torch compile caching...
   persists those artifacts so a new replica loads them instead of recompiling,
   which cuts compilation from minutes to roughly 5 to 20 seconds." For Truss
   `model.py` deployments the documented API is `load_compile_cache()` /
   `save_compile_cache()` from `b10-transfer`; the `b10-compile-cache & vllm
   serve ...` CLI form is documented for vLLM *custom servers*
   (`docker_server`), which ours is not — use the Python API path.
   Source: https://docs.baseten.co/development/model/runtime-caching
3. **Keep-warm knobs**: `min_replica ≥ 1` eliminates the from-zero cold start;
   pre-warm by PATCHing `min_replica` up "10-15 minutes before expected spike";
   raise `scale_down_delay` (default 900 s) to ride out dips.
   Source: https://docs.baseten.co/deployment/autoscaling/cold-starts

## Step 4 — Scale-to-zero and deactivate

**Scale-to-zero (keeps the deployment callable, wakes on demand):**

```sh
python3 deploy/baseten/manage.py autoscaling w52yvzr --model-id 3ydn1e43 \
  --min-replica 0 --max-replica 1
# raw: PATCH /v1/models/3ydn1e43/deployments/w52yvzr/autoscaling_settings
#      {"min_replica": 0, "max_replica": 1, "scale_down_delay": 900, ...}
```

- API: `PATCH .../deployments/{deployment_id}/autoscaling_settings` with
  `min_replica`, `max_replica`, `concurrency_target`,
  `target_utilization_percentage`, `autoscaling_window`, `scale_down_delay`.
  Source: https://docs.baseten.co/deployment/autoscaling/overview
- Trigger to sleep: "Once traffic stays at zero for the full
  `scale_down_delay`, the autoscaler shuts down every replica."
  Source: https://docs.baseten.co/deployment/autoscaling/cold-starts
- Trigger to wake: "The next request finds nothing running and waits for a full
  startup" — requests park at the router rather than erroring, failing with a
  `500` only if the parking timeout expires first. Explicit pre-wake is
  available via `POST .../wake`.
  Sources: https://docs.baseten.co/deployment/autoscaling/request-lifecycle ,
  https://docs.baseten.co/reference/inference-api/overview
- Cost while asleep: "A deployment scaled to zero replicas incurs no charges,
  but model load on a fresh replica is metered." Wake-up latency is a full cold
  start ("can take minutes for large models") and "During that wake-up period,
  billing is per minute even though the replica isn't yet serving responses."
  Source: https://docs.baseten.co/deployment/autoscaling/overview

**Deactivate (hard off, for end-of-drill):**

```sh
python3 deploy/baseten/manage.py deactivate w52yvzr --model-id 3ydn1e43 --yes
# raw: POST /v1/models/3ydn1e43/deployments/w52yvzr/deactivate
```

- Source: https://docs.baseten.co/reference/management-api/overview
  (deactivate endpoint table)
- Semantics: a deactivated deployment "Remains visible in the dashboard.
  Consumes no compute resources but can be reactivated anytime. API requests
  return a 404 error while deactivated."
  Source: https://docs.baseten.co/deployment/deployments
- **Storage while deactivated:** the docs list no storage or at-rest charge for
  deactivated deployments — the billing page meters only replica/builder/
  training minutes. The docs simply do not address storage cost for idle model
  images/weights; treat "deactivated bills $0" as documented-by-omission, not
  guaranteed. Source: https://docs.baseten.co/organization/billing

## Step 5 — Chaos drill: spill target = Model APIs

Spill endpoint: `https://inference.baseten.co/v1/chat/completions`
(OpenAI-compatible; billed per million tokens, cached input tokens discounted
automatically).
Source: https://docs.baseten.co/inference/model-apis/overview

- **Rate limits are per workspace tier, not per model** (RPM = requests/min,
  TPM = input+output tokens/min):

  | Account            | RPM | TPM       |
  |--------------------|-----|-----------|
  | Basic (unverified) | 15  | 100,000   |
  | Basic (verified)   | 120 | 500,000   |
  | Pro                | 120 | 1,000,000 |
  | Enterprise         | custom | custom |

  "If you exceed these limits, the API returns a `429 Too Many Requests`
  error." Increases go through the contact form.
  Source: https://docs.baseten.co/inference/model-apis/rate-limits-and-budgets
- **Budgets**: "Budgets apply only to Model APIs, not dedicated deployments";
  email at 75/90/100%; *enforced* budgets reject requests at the cap — an
  enforced budget can therefore take your failover path down mid-drill. Keep
  the drill budget non-enforced or sized for the spill.
  Source: https://docs.baseten.co/inference/model-apis/rate-limits-and-budgets
- **No documented burst/priority/failover guidance exists** for Model APIs — no
  Retry-After contract, no burst allowance, no priority tiers in the docs. Plan
  for hard 429s at 15 RPM (our tier history, friction #10) and client-side
  exponential backoff. (429 handling detail beyond "contact us to raise
  limits" is not in the snapshot; the errors page's 429 anchor doesn't exist in
  the captured page.)
- Size the drill: at Basic-unverified, 15 RPM is below one warm T4 replica's
  throughput — spill absorbs a trickle, not the full load.

---

## Gotchas

1. **"Unhealthy" while warming is expected surface behavior.** Custom
   `is_healthy()` doesn't run until `load()` completes, readiness/liveness
   probes don't run until the startup probe passes, and requests that arrive
   before a replica is ready are parked and can 500 on parking-timeout. Gate on
   status + wake + synthetic 200 (Step 2) instead of "activate returned
   success". Sources: https://docs.baseten.co/development/model/health-checks ,
   https://docs.baseten.co/deployment/autoscaling/request-lifecycle
2. **Env pointer poisoning (friction #15, observed here).** After q86yjdy
   DEPLOY_FAILED, `production_deployment_id` kept pointing at the corpse while
   w52yvzr was ACTIVE — `/environments/production/predict` returned the exact
   500 "Model is unhealthy" string until an explicit
   `manage.py promote w52yvzr --model-id 3ydn1e43 --yes`. **Before declaring
   ready, verify the pointer**: `GET /v1/models/3ydn1e43/environments/production`
   and confirm it references w52yvzr; if not, promote
   (`POST .../deployments/w52yvzr/promote`). Also probe the deployment-scoped
   URL (`/deployment/w52yvzr/predict`) — if that serves while the env URL 500s,
   it's the pointer, not warming.
   Docs for the endpoints: https://docs.baseten.co/reference/management-api/overview ;
   promotion semantics: https://docs.baseten.co/deployment/environments ;
   local history: `docs/FRICTION_LOG.md` #15.
3. **Deactivated ≠ 5xx.** While deactivated the API returns **404**
   (https://docs.baseten.co/deployment/deployments). The spill router's
   health/failure classifier must treat 404 from the dedicated endpoint as
   "down, spill" — a 404-means-bad-model-id assumption
   (https://docs.baseten.co/inference/errors) will misdiagnose it.
4. **You pay for warming and for sick replicas.** Cold-start/model-load minutes
   are billed (https://docs.baseten.co/organization/billing), and "You're
   billed for the uptime of your deployment... even if it's failing health
   checks, until it scales down"
   (https://docs.baseten.co/development/model/health-checks). A crash-looping
   activate is not free — watch the first minutes of logs
   (`manage.py logs`).
5. **Default health thresholds are 30 minutes.** A wedged replica can absorb
   traffic for up to 30 min before traffic is pulled. Docs recommend
   `startup_threshold_seconds` = 2× worst observed cold start,
   `stop_traffic_threshold_seconds` ≈ 60 s,
   `restart_threshold_seconds` ≈ 1.5× that — set in `runtime.health_checks`
   in config.yaml (requires a push, not a live PATCH).
   Source: https://docs.baseten.co/development/model/health-checks
6. **Timeout numbers disagree in the docs** (600 s vs 1200 s sync predict, see
   Step 2). Set an explicit client timeout and don't design the chaos drill
   around the parked-request window being exactly either value.
   Sources: https://docs.baseten.co/deployment/autoscaling/request-lifecycle ,
   https://docs.baseten.co/reference/inference-api/overview
7. **Scale-to-zero can outrun your test** — "A newly deployed model scales down
   to zero before you can send your first test request... Set `min_replica = 1`
   during testing," then return it to 0.
   Source: https://docs.baseten.co/troubleshooting/deployments
