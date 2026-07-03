# Friction Log — deploying on Baseten (+ RunPod)

PM research artifact for the baseten-mvp mission. Every entry is REAL friction
encountered first-hand while building on Baseten's stack (truss push, config.yml
/ model.py, management API, autoscaling, activate/promote, logs) or the
adjacent RunPod/vLLM pool. No hypothetical entries — if we didn't hit it, it
isn't logged. Target: ≥10 entries by mission end.

Format per entry: what we were doing → what happened → cost (time/money/
confusion) → workaround → what the product could do instead.

---

<!-- entries begin -->

### 1. `pip install truss` lands on the wrong Python; CLI works, imports don't
**Doing:** installing the deploy tool on macOS. **Happened:** `pip install
truss` installed under system Python 3.9 (`~/Library/Python/3.9`), not the
repo's Python 3.13 — so the `truss` module isn't importable from `python3`,
and truss itself warns it's on an unsupported Python (3.9.6 < 3.10).
**Cost:** ~10 min chasing a `ModuleNotFoundError` before realizing the CLI
binary works even though the import doesn't. **Workaround:** drive truss via
its CLI only; never `import truss` from repo code (the adapters are
stdlib-only anyway, so nothing depends on it). **Product could:** a
`truss doctor` that reports "installed on Python 3.9, which is unsupported;
your active python is 3.13" would have saved the whole detour.

### 2. `truss push` ignores `BASETEN_API_KEY`; needs a separate `truss login`
**Doing:** authenticating for a push with the documented env var already set.
**Happened:** `truss whoami` reported "No remote configured" despite
`BASETEN_API_KEY` being exported — truss authenticates via a `~/.trussrc`
remote created by `truss login`, not the env var that the *management API*
and our adapters use. Two different auth mechanisms for the same key on the
same platform. **Cost:** a confusing "why is my key not working" moment; a
naive CI pipeline that exports the env var would fail at push with a message
pointing at interactive login. **Workaround:** `truss login --api-key
"$BASETEN_API_KEY" --non-interactive` generates `~/.trussrc` from the env
var, keeping env as the source of truth (chmod 600). **Product could:** have
`truss push` fall back to `BASETEN_API_KEY` when no remote is configured —
the key is right there — or at least say "found BASETEN_API_KEY; run
`truss login --api-key $BASETEN_API_KEY` to use it."

### 6. First deploy hung ~30 min then went INACTIVE — no capacity, no signal
**Doing:** first `truss push` of Qwen3-8B (fp16) on the default L4. **Happened:**
build succeeded, then the deploy sat in `DEPLOYING` with **0 replicas and no
container/model logs for ~30 minutes**, then flipped to `INACTIVE` — never
served a request. Root cause: Baseten's L4 SKU is a **2× L4 instance**
(`L4:2x24x96`), so a config asking for 1 GPU still needs a scarce 2-GPU node
to be scheduled; that scheduling never happened and the platform silently
gave up. **Cost:** ~30 min of dead waiting and a lot of trust — this is the
single worst moment in the whole exercise, and it's on the capability the
platform markets hardest (fast, reliable inference). **Signal quality:** the
status API only says `DEPLOYING`/`INACTIVE`; there is no "waiting for
capacity," no queue position, no ETA, no "we couldn't place your 2×L4." A
user cannot tell "slow" from "stuck" from "doomed." **Workaround:** abandon
the 2×L4 path entirely; redeploy a **quantized** Qwen3-8B (`Qwen/Qwen3-8B-AWQ`,
int4 ~6GB) on a **single T4** — a common, well-stocked SKU that schedules in
minutes. **Product could (this is the PM headline):** (a) surface capacity/
scheduling state as first-class deploy status with an ETA or a "no capacity,
try GPU X" nudge; (b) never let a deploy die silently — INACTIVE with no
error is the worst outcome; (c) make single-GPU L4 a real option so an 8B
model doesn't require a 2-GPU node. The gap between the marketing ("deploy on
H100s and top-tier hardware") and this first-run experience is the exact
thing an infra PM exists to close.

### 7. Single-T4 scheduled fast but OOM-crashed on load — fixed-SKU RAM trap
**Doing:** redeploy after #6, this time int4-AWQ Qwen3-8B on a single T4 to
dodge the 2×L4 scheduling hang. **Happened:** the T4 node scheduled in ~1 min
(great — the single-GPU SKU is well-stocked), the container started, then
`model.load()` crash-looped: "Exception while loading model … **Killed** …
Inference server crashed, restarting." Repeated `Killed` = host OOM: the
`T4x4x16` SKU pairs the GPU with only **16 GiB of system RAM**, and loading
even a ~6 GB quantized 8B spikes host memory past that during weight
materialization. **The trap:** Baseten's GPU SKUs bundle a FIXED amount of
system RAM you can't raise independently — T4 = 16 GiB (too little to load an
8B), and the next step up (L4) is the 2-GPU node that wouldn't schedule (#6).
There's no "T4 + more RAM" option. **Cost:** another ~10 min and a second dead
deploy; a crash-looping deploy also holds a live GPU, so I deactivated it
immediately to avoid billing. **Product could:** (a) let system RAM be sized
independently of the GPU, or publish per-SKU RAM prominently so you can tell
an 8B won't load on a 16 GiB-RAM box BEFORE deploying; (b) pre-flight the
model's memory footprint against the chosen instance and warn at push time
("Qwen3-8B needs ~Xgb host RAM; T4x4x16 has 16 — pick A10G"); (c) surface OOM
as a clear deploy error, not an opaque restart loop. Two deploys, two
different fixed-SKU walls — this is the core infra-PM problem: the hardware
menu doesn't match the shape of real models.

### 8. RunPod payment flow stalls, and credits (not just a card) are required
**Doing:** funding RunPod to launch the second pool. **Happened:** the "Add
payment method" dialog hung on "Processing…" with "Your payment method was
added but is taking longer than expected to appear" — for TWO different cards
(Visa, then Amex), stuck each time. And even once a card is on file, RunPod is
**prepaid**: `clientBalance` stayed 0 until credits were explicitly purchased,
so a card alone can't launch a pod. **Cost:** ~30 min of retrying a broken
dialog + confusion over "card added but balance still 0." **Workaround:** wait
out the sync, then buy credits (balance went to $40). **Product could:** make
the payment-method confirmation reliable/idempotent, and state up front that a
positive prepaid balance — not just a card — is required to launch pods.

### 9. RunPod's API is split: REST for pods, GraphQL for catalog/balance
**Doing:** picking a GPU and provisioning via the REST API. **Happened:** the
GPU catalog and account balance are **not** in the REST API (`GET
/v1/gpus` 404s with a spec error), only in the legacy **GraphQL** API
(`gpuTypes`, `myself.clientBalance`), while pod create/list IS REST
(`rest.runpod.io/v1/pods`). You must speak two APIs to do one task. Then the
REST create-pod schema rejected `dockerArgs` ("not in input schema") — the
correct field is **`dockerStartCmd`** (an array appended to the image
entrypoint), which differs from older docs/examples. **Cost:** two failed
calls + a GraphQL detour. **Workaround:** GraphQL for catalog/balance, REST
for pods, `dockerStartCmd` array for container args. **Product could:** unify
on one API surface and align the create-pod field names with the docs.

### 3. Truss config internals moved between minor versions
**Doing:** validating `config.yaml` before spending on a push. **Happened:**
`TrussConfig` is documented/blogged as `truss.truss_config` but in 0.18.17
lives at `truss.base.truss_config` — older snippets break. **Cost:** minor,
one failed import. **Workaround:** validate via the installed package path,
not a remembered import. **Product could:** keep a stable public re-export
(`from truss import TrussConfig`) so validation snippets survive upgrades.

### 4. Auth succeeds but deploy is gated on billing — discovered only at push
**Doing:** first `truss push` of the primary pool. **Happened:** auth and
config validation both passed, the truss uploaded, then the API rejected it:
`You must add a payment method to deploy models.` The billing requirement
surfaces only at the final deploy step — after install, login, config
validation, and upload — not at login or `whoami`. **Cost:** a full
push cycle spent to discover an account-setup gap; in CI this would fail a
pipeline late with an error that looks like a code problem but isn't.
**Workaround:** none in code — the account owner adds a card at
app.baseten.co billing. **Product could:** surface billing status at
`truss login`/`whoami` ("logged in; no payment method — deploys will be
rejected") so the gap is caught before building/uploading, and make the
error link straight to the billing page.
**Follow-up:** the workspace then received a "You've got free credits! …
deploy a dedicated model on H100s" promo email. Retried the push — SAME
`add a payment method` error. Free credits do NOT satisfy the
payment-method gate for dedicated deployments; a card is still required
first. This is a real expectation mismatch: the growth email invites you
to deploy, but the platform blocks it until billing is set up, with no
hint in the email or the error that credits ≠ deploy access. **Product
could:** either let credits unlock dedicated deploys, or make the credits
email say "add a payment method to activate your credits for dedicated
deployments."

### 5. `truss push` default changed from development to published deployment
**Doing:** the same first push. **Happened:** truss announced "Deploying as a
published deployment. Use --watch for a development deployment." — the safe,
cheap default (a scratch *development* deployment) is now opt-in via
`--watch`; the default creates a **published** deployment. Easy to
accidentally stand up a billed production deployment when you meant to
experiment. **Cost:** none yet (billing gate stopped it first), but a
footgun. **Workaround:** use `truss push --watch` for iteration, publish
explicitly when ready. **Product could:** keep development-by-default for a
model's first push, or prompt "publish or development?" on an account's
first deploy.

### 10. Model APIs: tight per-model rate limits, no Retry-After, quota only visible in the console
**Doing:** chaos drills against two router pools backed by the same hosted
Model API (`zai-org/GLM-4.7`), ~1.3 aggregate rps of 1-token requests.
**Happened:** 28 of 40 requests returned 429 (evidence:
`benchmarks/raw/rate_limit_glm47_20260702-183916.csv`, one row per request
with status + latency; an earlier unrecorded probe measured 25/40) with an
empty rate-limit header set — no `Retry-After`, no `X-RateLimit-*` — and the
only quota surface is the console's "Requests (/h)" column, which the API
itself never reports.
Worse, the limit is per model per workspace, so two pools that look
independent to a router are secretly coupled: quarantining pool A and
spilling to pool B spends the SAME quota, and the incident agent's
verification probes then compete with the spilled traffic — recovery probes
kept timing out and quarantines stuck until traffic stopped. **Cost:** three
drill-suite runs misdiagnosed as agent bugs; ~40 minutes. **Workaround:**
drill at ≤0.5 rps against live pools, run repeatable MTTR evidence on the
sim, slow probe cadence after escalation. **Product could:** return
`Retry-After` + `X-RateLimit-Remaining` on 429s, expose the hourly quota via
API, and document that Model API limits are per-model-per-workspace (shared
across all callers).

### 11. Model APIs: reasoning deltas and a jittery /v1/models make naive OpenAI clients misbehave
**Doing:** pointing an OpenAI-compatible adapter at `inference.baseten.co`.
**Happened:** (a) reasoning models (gpt-oss-120b, GLM-5.2) stream
`delta.reasoning`/`delta.reasoning_content` before any `delta.content` — a
client that only watches `content` sees an empty completion at small
`max_tokens` and never latches TTFT; (b) `GET /v1/models` intermittently
takes >5s, so using it as a health probe (the obvious OpenAI-ism) flaps —
pools got marked down while chat was serving fine. **Cost:** one measurement
bug (TTFT never latched) and a class of false pool-down incidents in drills.
**Workaround:** count reasoning deltas as first-token for TTFT; treat the
listing as config (snapshot it) and never as a liveness signal. **Product
could:** document reasoning-delta streaming on the Model API page and serve
/v1/models from a cache with a latency SLO.

### 12. BUILD_FAILED is a dead end via API — build logs are console-only
**Doing:** third dedicated-deploy attempt (deployment `qz47j5o`, Engine-Builder
path, H100, TRT-LLM fp8_kv build of Qwen3-8B) failed with status
`BUILD_FAILED`. The failure email says "view the logs for more information."
**Happened:** the management API has no build-log surface:
`GET /v1/models/{id}/deployments/{id}/logs` returns `{"logs": []}` for a
build-failed deployment (runtime logs of a thing that never ran), and no
`build_logs`/`builds` endpoint exists. The only diagnostics live behind the
web console. For a CI/CD-driven flow (this repo's whole premise) a failed
build is therefore un-triageable programmatically — you can detect
BUILD_FAILED via status polling but not WHY. **Cost:** third failed deploy
cycle on this SKU path; likely causes (py313 unsupported by the engine
builder? fp8_kv × Qwen3 combo?) are unconfirmable without a human clicking
the console. **Workaround:** none via API; a human reads the console logs.
**Product could:** expose build logs in the management API (or at minimum a
`failure_reason` field on the deployment object) and validate
python_version/quantization compatibility at config-push time instead of
30 minutes into a build.
**Scorecard for the dedicated path: 3 attempts, 3 distinct failure layers**
(L4: scheduler never placed; T4: host-RAM OOM crash-loop; H100: engine build
failed, cause invisible) — while the hosted Model APIs served the same
workload with zero provisioning the same day. That contrast IS the PM story.

### 13. GPU families are org-gated, discovered only at push
**Doing:** 4th dedicated attempt — custom vLLM Truss targeting `A10Gx8x32`,
picked straight from the public instance-type reference (1 GPU, 32 GiB host
RAM, $0.02424/min — the documented sweet spot for an 8B AWQ model).
**Happened:** `truss push` rejected it: "Feature unavailable: The GPU type
'A10G' is not supported for your organization. Please contact Baseten
support." Nothing in the docs' instance table, the console, or config
validation marks which families a workspace can actually use; the gate
surfaces only after packaging and uploading. **Cost:** one wasted push
cycle; retargeted to `T4x8x32`. **Workaround:** trial-and-error per family
(T4 known-good for this org). **Product could:** expose allowed instance
types via API/console (the management API's instance-types endpoint would be
the natural place), annotate the docs table, and validate at `truss push`
config-check time before upload.

### 14. Unpinned transitive dep = deploy-time import crash (build green, deploy dead)
**Doing:** 4th dedicated attempt, custom vLLM Truss on T4x8x32 (q86yjdy) —
the SKU fix worked, build passed, node scheduled. **Happened:** model.load()
crash-looped on `from vllm import AsyncEngineArgs`:
`ValueError: 'aimv2' is already used by a Transformers config` — config.yaml
pinned `vllm==0.9.1` but transformers floated, pip resolved a version newer
than vllm 0.9.1's Ovis shim tolerates, and the collision only fires at
IMPORT, i.e. at deploy, after a green build. The failure email again says
"view the logs" — this time runtime logs DID exist via the API (progress vs
friction #12). **Cost:** one dead deploy cycle (~15 min); fix was a one-line
`transformers==4.53.2` pin (w52yvzr). **Workaround:** pin the full working
set, not just the top-level dep. **Product could:** import the model class
during BUILD (a 5-second smoke that would have failed fast and cheap), or
resolve/lock requirements at push time and show the diff vs the last
successful deploy.

### 15. A failed first deploy poisons the production environment pointer
**Doing:** repushing the dependency-pinned truss (w52yvzr) after q86yjdy
DEPLOY_FAILED. **Happened:** the console/email said the new deployment was
ACTIVE and logs said "Deploy was a success" — but
`/environments/production/predict` kept returning
`500 "Model is unhealthy"`, because `production_deployment_id` still pointed
at the DEAD q86yjdy: the first-ever push had claimed the production
environment, failed, and kept the pointer; the successful fix did not take
over. Nothing in the push output, status API, or failure email mentions
that production is now serving a corpse — the working deployment answers
only on its deployment-scoped URL until you explicitly
`promote`. **Cost:** ~10 min of "ACTIVE but unhealthy" confusion straight
after a hard-won first success. **Workaround:**
`manage.py promote w52yvzr --model-id 3ydn1e43 --yes`, then the env URL
serves (warm TTFT ~330ms, TPOT ~34ms/tok on T4x8x32 — inside the voice
SLO). **Product could:** never leave an environment pointing at a
DEPLOY_FAILED deployment when a newer ACTIVE one exists (or at least flag it
in `truss push` output: "note: production still serves failed q86yjdy —
promote to switch").

### 16. RunPod provisioning outage: five consecutive pods "rented, runtime null" — billing while dead
**Doing:** re-provisioning the vLLM pool that had worked earlier the same day
(pod 3hs5xl4usl6l5j, created 18:44 UTC, served fine until terminated).
**Happened:** from 23:06 UTC, five consecutive pods across SECURE and
COMMUNITY clouds and four GPU families (RTX 4090 ×2, RTX A5000, RTX 3090,
L4) sat `desiredStatus: RUNNING` with `runtime: null` for 15-30+ minutes
each — rented and BILLING, container never started. Ruled out: our spec
(identical to the working pod), the image (`vllm/vllm-openai:latest` last
moved 06:00 UTC per Docker Hub, before the working pod; a pinned v0.9.1
stalled identically), GPU family, and cloud tier. One COMMUNITY create
failed honestly ("machine does not have the resources"); SECURE just takes
the money and never starts. The API exposes no provisioning state, no error,
no events — `machine: {}`, `runtime: null` is all you get. **Cost:** ~$0.60
across five dead pods + ~90 min of forensic work. **Workaround:** none —
capacity-side. Detection rule now encoded in pod.py + LIVE_SETUP.md: if
`runtime` is null after ~10 min, kill the pod (it will not recover).
**Product could:** not bill until the container starts, expose provisioning
events via API, and fail create loudly when a host can't start the workload.
