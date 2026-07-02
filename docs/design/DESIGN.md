# Devboard v2 — Design Contract

**Visual source of truth: `refined/Devboard.dc.html` + `refined/README.md`**
(the "Mission Control Console" handoff, adopted 2026-07-01 — see deviations
log). `devboard-mockup.html` (this directory) remains the **data-content
authority**: every data element, endpoint shape, and state behavior it
describes is binding and must appear in the refined board. Where the two
disagree on visuals, the refined handoff wins; where they disagree on data
semantics, this document's reconciliation rules (deviations log) win.
`refined/support.js` is the prototype's runtime shim only — do not port it.

## Principles
1. **Runtime, not deploy-time.** This is a mission-control surface: dense,
   dark, alive. It deliberately contrasts with deploy-console UIs (light,
   whitespace-heavy, navigation-driven).
2. **Hierarchy is the design.** Hero strip → SLO panel → placement →
   release/incidents. A founder should read the three hero numbers from
   across the room.
3. **Motion is meaning.** Everything that animates represents traffic or
   state change. Nothing animates for decoration.
4. **Every number is auditable.** Any figure rendered must trace to
   `benchmarks/raw/*.csv` or a live endpoint. No fabricated values in
   production mode (mock generator is dev/replay only).

## Tokens
| Token | Value | Use |
|---|---|---|
| bg / panel / panel2 | #0A0E12 / #10161D / #141C25 | surfaces |
| line | #1E2933 | borders |
| txt / dim / micro | #E8EEF2 / #8A9BA8 / #5C6B77 | text tiers |
| ok / warn / bad / accent | #2DE0A5 / #F5B841 / #FF5D5D / #39C4FF | health + traffic |
| type | Inter (UI), mono for IDs/values, tabular-nums everywhere | |
| grid | 8px spacing grid; 16px gutters; 6px panel radius | |

Red is reserved for SLO breach / ejection only. Amber = degrading. One accent.

## Layout (1440×900, no scroll for hero + SLO)
- Top bar: product name, UTC clock, dev-only state switcher.
- Hero strip (3 cards): TPOT p99 vs SLO · $/1M tok at SLO · MTTR with delta
  vs manual. Each with 24h sparkline.
- Left panel: per-pool TTFT/TPOT percentile strips (p50/p95/p99 markers
  against red SLO line) + goodput-vs-concurrency curve with operating point.
- Right panel: two pool cards (health, util, $/1M tok, autoscaler state) +
  scrolling placement-decision feed (8 rows, newest on top).
- Bottom lane: canary stepper with gate verdicts · incident cards
  (detect/diagnose/resolve duration bar, MTTR badge, agent action log) ·
  MTTR history chart (manual vs agent lines, gap shaded).

## States (dev switcher → real system states)
| Mockup state | Real trigger | Visual |
|---|---|---|
| healthy | steady load | all green, canary progressing |
| degrading | latency injection (chaos) | vllm pool amber, spill decisions in feed, promotion paused |
| incident | chaos kill + incident agent | pool red/ejected, live incident card filling, release frozen |
| replay | recorded trace of a REAL chaos drill (captured in F4/F6) | 90s scripted playback with progress bar — used for the demo video |

Replay must play back recorded data. Never fabricate a replay.

## Data contract (canonical shapes live in the mockup's generator; extract to `contracts/devboard.openapi.yaml`)
| Endpoint | Feeds | Poll |
|---|---|---|
| GET /v1/metrics/hero | hero strip | 2.5s |
| GET /v1/metrics/slo | percentile strips + goodput | 5s |
| GET /v1/pools | pool cards | 5s |
| GET /v1/placement/feed | decision feed | SSE/stream |
| GET /v1/releases/active | canary stepper + gate | 5s |
| GET /v1/incidents | incident cards + MTTR chart | 5s |

## Implementation notes
- Single-file, zero-backend page served by the router (keep the repo's
  zero-install philosophy). Vanilla JS or React-via-CDN acceptable; no build
  step; no chart libraries (SVG is sufficient and is part of the look).
- Anti-goals: no sidebar/navigation, no pie charts, no light theme, no more
  than 3 chart styles, no lorem ipsum, no gradient decoration.

## Deviations log
| Date | Change | Rationale |
|---|---|---|
| 2026-07-01 | A refined devboard design (in progress, Claude design) may supersede this mockup's visual layer when delivered. The refinement may change layout/polish only — every data element, endpoint shape, and state behavior in this mockup remains binding and must appear in the refined board. | Owner instruction, 2026-07-01. |
| 2026-07-01 | Refined handoff (`refined/`) adopted as the visual standard: new tokens (teal #2FE0C6 / amber #FFB020 / red #FF5257 / violet replay #B08CFF, JetBrains Mono for mono), density strips instead of percentile bars, above/below-the-fold split, vertical canary stepper, animated placement connector. Verified rendering all four states. | Owner delivered the refinement; instruction of 2026-07-01 applies. |
| 2026-07-01 | **Endpoints stay per `contracts/devboard.openapi.yaml`.** The refined README suggests differently-named feeds (`/v1/slo/rollup`, `/v1/slo/histograms`, `/v1/goodput`, `/v1/cluster/status`, `/v1/placement/decisions`, `/v1/incidents/mttr`). Mapping: hero ← `/v1/metrics/hero`; density strips + goodput ← `/v1/metrics/slo` (optional `hist` field added for the density curves); pool cards ← `/v1/pools`; feed ← `/v1/placement/feed` (SSE); canary ← `/v1/releases/active`; incident lane + MTTR history ← `/v1/incidents`. Topbar cluster pill and MTTR chart are client-side derivations — no new endpoints. | The six-endpoint contract is committed and binding (mission spec); the refined names are a design-side suggestion, not a contract change. |
| 2026-07-01 | **TTFT SLO of record is p99 < 500ms** (voice tier, per mission + original mock). The refined prototype hard-codes "TTFT ≤ 300ms"; the implementation must render SLO thresholds from API data, not hard-code either value. 300ms may be introduced later as a stretch tier via policy, not via the board. | Mission metrics anchor conflicts with refined copy; data semantics win. |
| 2026-07-01 | Refined shows different models per pool (GPT-OSS-120B / Qwen3-8B); F1 requires the **same model on both pools** for a fair baseline. Board renders whatever model names the API reports — the two-model look returns naturally in later features if a second model is deployed. | F1 baseline validity. |
| 2026-07-01 | Refined replay is a simulated 90s loop (prototype only). Production REPLAY must play back a recorded chaos-drill trace (captured in F4/F6) mapped onto the same 90s presentation. | Binding rule from the mission; never fabricate a replay. |
| 2026-07-01 | Original mock's "LAST ROLLBACK" line is absent from the refined canary card (a rollback note moved into the incident footer). Implementation keeps `last_rollback` in `/v1/releases/active` and renders it under the SLO gate box. | Refined visuals win, but the mock's information content is binding. |
| 2026-07-01 | Production board (`/devboard`, services/router/router_app/static/devboard.html): DEV switcher renders all four states but DEGRADING/INCIDENT are disabled until tools/chaos.py wires their real triggers (F4/F6) and REPLAY until a recorded drill trace exists. Vanilla JS + SVG (no React) — DESIGN.md explicitly allows either; zero CDN scripts keeps the router's zero-install story. | No fabricated states: a switcher button that only repaints the UI would violate the "real system states" rule. |
