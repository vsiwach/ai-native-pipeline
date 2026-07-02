# SLO-AUDITOR — feature: model-apis (branch baseten-mvp)

**Verdict: FAIL** (one untraceable count in `docs/FRICTION_LOG.md`; all claimed
MTTR / catalog / cost-attribution numbers otherwise fully traced and reproduced).

Audited: 2026-07-02, sim stack at `http://localhost:8096` (pools 8103/8104,
`DEVBOARD_MODEL=glm-4.7`). HARD CONSTRAINT honored: no live cloud calls —
`BASETEN_API_BASE_URL` never set; backends verified as `"backend":"MaxLocalSim"`
via `GET :8103/v1/info` and `:8104/v1/info` before any traffic.

## Commands run

```
curl -s http://localhost:8096/v1/pools
curl -s http://localhost:8096/v1/incidents
curl -s http://localhost:8096/v1/metrics/hero
curl -s http://localhost:8096/v1/metrics/slo
curl -s http://localhost:8103/v1/info ; curl -s http://localhost:8104/v1/info
python3 tools/chaos.py drill --router http://localhost:8096 --scenario latency \
    --model glm-4.7 --latency-ms 2600 --rps 2 --timeout-s 120
cd services/llm && python3 -m pytest tests/test_openai_compat.py -q   # 21 passed in 0.01s
```

## (a) Chaos-drill MTTR — regenerated vs displayed

| Claim | benchmarks/raw/chaos_drills.csv row | Timeline CSV (resolved event) | /v1/incidents | Match |
|---|---|---|---|---|
| suite 16:31 latency MTTR 8.1s (sim) | `20260702-163119,...,8.1,True,19,0` | `chaos_drill_latency_20260702-163119.csv`: `resolved,MTTR 8.1s (agent=True)` | INC-0001 `mttr_s: 8.1` | EXACT |
| suite 16:32 errors MTTR 8.1s (sim) | `20260702-163219,...,8.1,True,22,0` | `chaos_drill_errors_20260702-163219.csv`: `resolved,MTTR 8.1s` | INC-0002 `mttr_s: 8.1` | EXACT |
| suite 16:33 combo MTTR 8.1s (sim) | `20260702-163309,...,8.1,True,19,0` | `chaos_drill_combo_20260702-163309.csv`: `resolved,MTTR 8.1s` | INC-0003 `mttr_s: 8.1` | EXACT |
| 15:30 latency run MTTR 8.7s | `20260702-153057,...,8.7,True,18,5` | `chaos_drill_latency_20260702-153057.csv`: `resolved,MTTR 8.7s (agent=True)` | (pre-restart router; not in live store) | EXACT vs CSVs |

**Re-run from raw commands (this audit):** drill printed `MTTR 8.1s`, appended
`20260702-164306,latency,model-api-a,glm-4.7,2600.0,0.0,True,17.7,17.7,17.73,8.1,True,19,0`
to `chaos_drills.csv`, wrote `chaos_drill_latency_20260702-164306.csv`
(`24.31,resolved,MTTR 8.1s (agent=True)`), and the router recorded INC-0004
with `mttr_s: 8.1`, `agent: true`, `live: false`. Printed = CSV = timeline =
`/v1/incidents` = `/v1/metrics/hero mttr_s: 8.1`. An independent second run at
16:43:28 (`20260702-164328`, not run by this audit) also resolved at 8.1s —
corroborating.

**Tolerance applied:** MTTR itself: exact match required and observed (8.1s on
every sim resolution — the agent's probe cadence is deterministic on the sim).
Detect/quarantine timings vary run-to-run (17.7s this audit vs 18.76s in the
16:31 row, and 45.91s in the 16:43:28 run) because breach detection depends on
the sampling window; these are NOT displayed as claims, so no tolerance was
needed on any displayed number.

Every `chaos_drills.csv` row has a matching per-drill timeline CSV in
`benchmarks/raw/` (19 rows before audit, all 19 stamped timeline files present;
now 21/21). Unresolved/FAIL rows (e.g. `20260702-160159` live-429 run,
`timeout,no resolution within 150.0s — FAIL`) are honestly recorded, not
massaged.

## (b) Model catalog provenance

`deploy/baseten/model-apis.json` carries `"source": "GET
https://inference.baseten.co/v1/models"` and `"fetched_at":
"2026-07-02T19:11:03Z"`; structure matches exactly what
`deploy/baseten/manage.py cmd_catalog` (lines 107–151) emits ($/token → $/1M
conversion at lines 131–133). The backends re-expose this provenance live:
`GET :8103/v1/info` returns `catalog_source` + `catalog_fetched_at` identical
to the file. Could not re-run `manage.py catalog` (live-call ban) — verified by
code inspection instead; not a blocker since the pricing claim is about the
committed snapshot. **Weakness (noted, not failing):** `--fetched-at` is
operator-supplied, not clock-derived (`manage.py` line 187), so the timestamp
is asserted rather than recorded.

## (c) Cost attribution

`services/llm/llm_app/openai_compat.py` `generate()` (lines 231–236): when
per-token prices are set, `est_cost_usd = prompt_tokens/1e6 * usd_per_1m_prompt
+ completion_tokens/1e6 * usd_per_1m_completion`; per-token wins over the $/hr
share path. Unit-verified by
`services/llm/tests/test_openai_compat.py::ModelAPIEconomicsTest::test_per_token_prices_win_over_hourly_share`
(100 prompt + 200 completion @ glm-5.2 catalog prices 1.4/4.4, asserted to 12
places). Full suite: **21 passed**. Wiring: `llm_app/factory.py` builds the
`baseten-api` mux from `MODEL_API_CATALOG` so sims carry the catalog's real
per-token prices; live path gated on `BASETEN_API_BASE_URL` (unset here).

## SLO definitions

`routing-policy.yaml` tiers: `realtime: ttft_ms: 500, tpot_ms: 60` — matches
the mission voice SLO exactly, with the mission cited in the comment. Displayed
SLOs come from policy via the registry tier (`/v1/metrics/hero` shows
`tpot_slo_ms: 80` because `glm-4.7` is registered tier `standard`
(`inference-registry.yaml` line 17) — traced to config, not hard-coded).
**Flag:** `tools/devboard/llm.html` lines 301–302 hard-code `slo_ttft_ms: 500`
— it is inside the explicit "Inject SLO breach" demo button (synthetic
incident), not a rendered metric, but per policy any UI-side SLO constant
should come from the API.

## Unreproducible claims (cause of FAIL)

1. **`docs/FRICTION_LOG.md` #10 (line 160): "25 of 40 requests returned 429".**
   No committed raw file anywhere in the repo contains per-request status codes
   or a run with 40 requests / 25 429s (`chaos_drills.csv` has no such row;
   timeline CSVs record only drill events). A displayed count with no CSV is an
   automatic FAIL under the provenance rule.
2. **Secondary (provenance gap, same entry): "~1.3 aggregate rps" and the
   live-vs-sim attribution of runs.** `chaos_drills.csv` has no live/sim column,
   so the claim that the 15:30-15:35 8.7s-era rows were "live" and 16:31+ rows
   "sim" cannot be established from the committed evidence alone (only the
   in-memory `/v1/incidents` records carry `live: false`, and only for the
   current router process). Recommend adding `live` and `rps` columns to
   `chaos_drills.csv` and a raw per-request CSV (status code column) for live
   drills; then #10's numbers become traceable.

Everything in the stated claim set (a)(b)(c) traced end-to-end; the FAIL is
scoped to the FRICTION_LOG counts above.
