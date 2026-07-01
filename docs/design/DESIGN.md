# Devboard v2 — Design Contract

`devboard-mockup.html` (this directory) is the source of truth for layout,
hierarchy, color, and motion. This document records the rules an implementation
must follow and the deviations log.

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
