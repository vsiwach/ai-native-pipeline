# SLO-AUDITOR — feature: model-apis (branch baseten-mvp)

**Verdict: PASS** (re-audit after remediation commit `f647380`; supersedes the
prior FAIL, which was scoped to one untraceable count in `docs/FRICTION_LOG.md`).

Re-audited: 2026-07-02, sim stack at `http://localhost:8096`
(`DEVBOARD_MODEL=glm-4.7`). HARD CONSTRAINT honored: no live cloud calls;
read-only against localhost only. The permitted one sim drill was NOT needed —
committed evidence plus the live router state sufficed.

## What changed since the FAIL

The FAIL had exactly one blocking finding: FRICTION_LOG #10 claimed
"25 of 40 requests returned 429" with no committed per-request raw file.
Commit `f647380` remediated:

1. #10 now reads **"28 of 40"** and cites
   `benchmarks/raw/rate_limit_glm47_20260702-183916.csv` ("one row per request
   with status + latency"). The old 25/40 is now explicitly labeled "an earlier
   unrecorded probe" — a disclosure, no longer a displayed metric.
2. A new drill row `20260702-184106` (errors, sim) landed in
   `benchmarks/raw/chaos_drills.csv` with its timeline CSV.

## Commands run (this re-audit)

```
git show --stat f647380
wc -l benchmarks/raw/rate_limit_glm47_20260702-183916.csv     # 41 (header + 40)
python3 - <<'EOF'   # independent recount from the raw CSV
import csv, collections
rows=list(csv.DictReader(open('benchmarks/raw/rate_limit_glm47_20260702-183916.csv')))
# rows: 40; Counter({'429': 28, '200': 12}); duration 29.43s; rps 1.325
EOF
python3 - <<'EOF'   # every chaos_drills.csv row must have a timeline CSV
# 24 rows, missing timelines: []
EOF
cat benchmarks/raw/chaos_drill_errors_20260702-184106.csv
curl -s http://localhost:8096/v1/incidents
curl -s http://localhost:8096/v1/metrics/hero
```

## Regenerated vs displayed

| Displayed claim | Where | Regenerated (this audit) | Match |
|---|---|---|---|
| "28 of 40 requests returned 429" | FRICTION_LOG #10 line 160 | 40 CSV rows; status counter `429: 28, 200: 12` | EXACT |
| "~1.3 aggregate rps" | FRICTION_LOG #10 line 159 | 39 intervals / 29.43 s = **1.325 rps** from `t_rel_s` | within "~" (stated ~1.3; recomputed 1.325 — a one-decimal rounding, the only tolerance applied) |
| drill `20260702-184106` MTTR 8.1s (sim) | `chaos_drills.csv` row 24 | timeline `chaos_drill_errors_20260702-184106.csv`: `11.65,resolved,MTTR 8.1s (agent=True)`; router `INC-0001` `mttr_s: 8.1`, `agent: true`, `live: false` | EXACT |
| `/v1/metrics/hero mttr_s: 8.1` | devboard endpoint | `mttr_median(agent=True)` over resolved incidents (`devboard.py:44,53`; `incidents.py:103-109`) = median{8.1} = 8.1 | EXACT (open incidents INC-0002/0003 show count-up `mttr_s` and are correctly excluded — `live` here means "still open") |
| all prior traced items (16:31/16:32/16:33 suite, 15:30 run, catalog provenance, cost attribution, 21 unit tests) | prior audit | files unchanged since prior audit; `chaos_drills.csv` 24/24 rows have matching timeline CSVs in `benchmarks/raw/` | HOLDS |

**Tolerance:** counts exact (required and observed). "~1.3 rps" accepted at one
decimal of the recomputed 1.325 because the doc itself writes it as approximate;
every underlying datum is in the CSV. MTTR exact.

## Unreproducible claims

None remaining. Every displayed number now traces to a committed raw file under
`benchmarks/raw/` with enough columns to recompute it.

## Follow-ups (acknowledged by the mission; judged non-blocking under the
provenance rule because no *displayed number* depends on them)

1. **No committed generator for `rate_limit_glm47_*.csv`** (not in
   `tools/chaos.py` or `deploy/baseten/manage.py`). The rule requires a raw CSV
   sufficient to recompute the displayed number — satisfied — but a live re-run
   of the probe is not scriptable from the repo. Recommend committing the probe
   as `tools/chaos.py ratelimit`.
2. **`chaos_drills.csv` has no live/sim column.** No doc/README/devboard surface
   displays the live-vs-sim MTTR attribution (the 8.7s-live claim exists only in
   the commit message, not an audited display surface), so nothing displayed is
   untraceable — but add the column before any doc cites a "live MTTR".
3. **`fetched_at` in `deploy/baseten/model-apis.json` is operator-asserted**
   (`manage.py --fetched-at`), not clock-derived. Timestamp label, not a metric.
4. **`tools/devboard/llm.html` lines 301-302 hard-code `slo_ttft_ms: 500`** —
   inside the synthetic "Inject SLO breach" demo payload, not a rendered metric;
   rendered SLOs come from `/v1/metrics/hero` (policy/registry-derived,
   `routing-policy.yaml` realtime: ttft 500 / tpot 60 matches the mission).
   Still flagged per policy; does not make any displayed number untraceable.

SLO definitions re-checked: unchanged and mission-conformant.
