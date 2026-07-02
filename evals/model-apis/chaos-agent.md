# CHAOS-AGENT verdict — feature: model-apis (branch baseten-mvp)

**Verdict: PASS** — every attacked invariant held observably. SIM only
(router http://localhost:8096, chaos pools 127.0.0.1:8103/8104,
DEVBOARD_MODEL=glm-4.7); no cloud calls, no spend. All faults injected and
cleared through `tools/chaos.py` (extended this run with a router dev-chaos
mode: `inject/clear/status --router --pool-id` → `POST /v1/dev/chaos`).

Context: the router restarted between eval sessions (incident counter reset
to INC-0001). Sessions 1 evidence (inv1/2/4/5) predates the restart; inv3 and
the drill re-spin were run this session, after commit f647380 (backend
5xx/429 propagate as real statuses with per-replica failover; 429 counts as
an SLO breach).

## Attacks → expected vs observed

| Inv | Attack (chaos.py) | Expected safe behavior | Observed | Evidence |
|---|---|---|---|---|
| INV1 catalog/aliases | none (surface conformance under load path) | all 6 catalog models + aliases serve via router, stream + non-stream, correct `model` echoed | 6/6 models HTTP 200 non-stream; SSE chunks well-formed for glm-5.2 | `evidence/inv1-catalog-aliases.txt` |
| INV2 SLO drills | `drill --suite` (latency 2600ms / errors 0.9 / combo) on model-api-a | detect → quarantine → spill → agent-verified resolve; MTTR measured; chaos fully cleared after | INC-0005/6/7 opened; detect 15.0–45.9s, MTTR 8.1s each; post-drill chaos state all zeros | `evidence/inv2-drill-suite.txt`, `evidence/inv2-incidents-after-drill.json`, `evidence/inv2-chaos-state-after-drill.json`, `evidence/chaos_drill_{latency,errors,combo}_*.csv` |
| INV2 re-spin post-f647380 | `drill --scenario latency --latency-ms 2600 --rps 2` | same lifecycle still resolves after the 5xx-propagation change | INC-0006 (new counter): detect 16.2s, quarantined, cleared, resolved, MTTR 8.1s | `evidence/inv2-drill-respin-post-f647380.txt`, `evidence/chaos_drill_latency_20260702-185334.csv` |
| INV3 last-pool guard + honest 5xx | `inject --router … --pool-id model-api-{a,b} --error-rate 1.0` (BOTH pools) | at most ONE pool quarantined; client gets real 5xx during blast, never a laundered 200 | 30-request blast: `500 ×4` then `503 ×26`, **zero 200s**. INC-0004 quarantined model-api-a; INC-0005 on model-api-b titled "last healthy pool, quarantine withheld". Census during fault: quarantined = `['model-api-a']`, count 1 → guard HELD. Post-clear: 15/15 HTTP 200, both incidents resolved (MTTR 72.5s incl. blast window) | `evidence/inv3-last-pool-guard.txt` |
| INV4 escalation path | `inject --target :8103 --latency-ms 2600` held past probe allowlist | 5 consecutive failed probes → `agent_escalation` event, quarantine held, on-call escalation; resolves after clear | INC-0008: probes every ~4s, 5 fails → "escalating to on-call … beyond agent allowlist"; `agent_escalation` event seq 537 on devboard event log; resolved after clear. Companion INC-0009 again showed quarantine withheld on last pool | `evidence/inv4-escalation.txt` |
| INV5 unknown model | request for unregistered `gpt-99-turbo` | structured 404, no silent fallback | Router: HTTP 404 `{"error":{"code":"unknown_model",…}}`. Finding: pool hit DIRECTLY returns 200 and silently serves `openai-gpt-120b` — mitigated because the router is the only public entry, but the backend contract is loose | `evidence/inv5-unknown-model.txt` |

## Restoration / MTTR
Every injection was cleared via chaos.py and verified on BOTH surfaces
(router `/v1/dev/chaos` and pool-direct `/chaos` all zeros); both pools back
in rotation (replicas 1, steady); all incidents resolved (INC-0001…0006 on
the current counter, none live). Drill MTTR 8.1s; both-pools blast MTTR
72.5s (dominated by the deliberate 30-request blast duration).

## Not tested (and why)
- **429-specific propagation/SLO accounting** (part of f647380): chaos.py's
  inject surface only produces 5xx (`error_rate`); there is no `inject-429`
  attack yet. The 5xx half of the claim is verified (INV3); the 429 half is
  untested. Add a `status_code` knob to the pool chaos endpoint + chaos.py
  before the live confirmation run.
- **LIVE confirmation**: out of scope per task (SIM only, no spend).

## Findings (system survived, but note)
1. **Chaos-state observability gap (most dangerous).** A residual
   `error_rate: 1.0` injected pool-direct on model-api-a (leftover from the
   prior session) was INVISIBLE on the router's `GET /v1/dev/chaos`, which
   reported both pools clean — the router view is local bookkeeping, not
   pool truth. The devboard showed only the symptom (health 40, incidents),
   never the cause. A fault injected or leaked outside the router's own
   dev endpoint cannot be diagnosed from the devboard.
2. **Health-score starvation.** After recovery, a "bad" pool receives almost
   no traffic, so its windowed health score stays low (stuck 13–23) long
   after it is actually healthy and back in rotation — the devboard
   understates recovered capacity.
3. Pool-direct unknown-model laundering (INV5 above).
