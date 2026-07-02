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
