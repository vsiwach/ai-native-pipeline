# Handoff: Devboard — Live Inference-Ops Console

## Overview
Devboard is the **real-time operations console** for an open-source inference control
plane (`ai-native-pipeline`). Unlike a deploy-time dashboard, it is a **mission-control
surface**: a single screen where latency SLOs, request placement, canary releases, and
incidents are *alive* and updating continuously. A founder should be able to read the
top three numbers from across the room; a staff infra engineer should be able to watch
traffic rebalance and an incident agent resolve a fault in real time without navigating
anywhere.

There is **no sidebar and no navigation** — everything lives on one continuously-updating
screen. A small dev-only state switcher (top right) forces the four operational states
for demos/testing; in production these states are driven by live telemetry.

## About the Design Files
The file in this bundle (`Devboard.dc.html`) is a **design reference built in HTML/React
(no build step, CDN React)** — a working prototype that shows the intended look, motion,
and behavior. It is **not production code to copy directly**. `support.js` is only the
prototype's runtime shim so the HTML opens standalone; **do not port it**.

Your task is to **recreate this design in the target codebase's environment** (React/Vue/
Svelte/etc.) using its established component library, state layer, and data-fetching
patterns. If no frontend exists yet, pick the framework best suited to a high-frequency
live dashboard (React + a lightweight charting primitive, or hand-rolled SVG, is a fine
default — see "Charts" below). All numeric/telemetry data in the prototype is **mock data
generated in JS**; wire the real feeds listed under "Data Sources".

## Fidelity
**High-fidelity.** Colors, typography, spacing, motion, and layout are final and
intentional. Recreate the UI pixel-accurately using the codebase's primitives, matching
the exact tokens below. The Bloomberg-terminal density and the strict 8px spacing grid
are core to the design — preserve them.

---

## Layout (single screen, top → bottom)

Root: full-viewport dark surface, `padding: 14px 18px 40px`, font Inter, `font-variant-numeric: tabular-nums` globally.

**Screen is split into "above the fold" and "below the fold":**
- The **topbar + hero strip + SLO panel** are wrapped in a `min-height: calc(100vh - 54px)`
  flex column so they fit a 1440×900 laptop **without scrolling**. This is a hard requirement.
- **Placement Map** and **Release + Incident lane** sit below the fold (scroll to reach).

### 1. Topbar (height ~44px)
`display:flex; align-items:center; gap:16px`.
- Left: wordmark **DEVBOARD** (Inter 700, 17px, letter-spacing .18em) + subtitle
  `ai-native-pipeline · inference control plane` (JetBrains Mono 500, 11px, #5C6A78).
- Vertical divider (1px × 20px, #1C2530).
- Cluster status pill: 7px dot (blinking, `animation: dvBlink 2.4s infinite`) + label.
  Color follows global state: teal `ALL SYSTEMS NOMINAL` / amber `DEGRADING · REBALANCING`
  / red `SLO BREACH · INCIDENT ACTIVE`.
- Spacer, then UTC clock (JetBrains Mono 500, 12px, #93A1B0, `HH:MM:SS UTC`, ticks every second).
- **Dev state switcher** (right): label `DEV` + four buttons — `HEALTHY`, `DEGRADING`,
  `INCIDENT`, `REPLAY 90s`. Active button: 1px border in its accent + accent@12% bg +
  accent text. Accents: healthy teal, degrading amber, incident red, replay violet #B08CFF.
  Inactive: border #243040, text #6B7A89.

### 2. Hero strip
`display:grid; grid-template-columns:repeat(3,1fr); gap:12px`. Three tiles.
Each tile: `#0E141B` bg, 1px #1C2530 border, 10px radius, `padding:16px 18px 12px`,
flex column. Structure top→bottom:
1. Row: micro-label (Inter 600, 10.5px, letter-spacing .15em, UPPERCASE, #5C6A78) +
   delta chip (JetBrains Mono 600, 10.5px, colored by direction) justified between.
2. Big number: Inter 650, **44px**, letter-spacing -.025em, colored by health +
   a unit suffix (Inter 500, 15px, #93A1B0), baseline-aligned, gap 8px.
3. Sub-line (Inter 500, 11.5px, #6B7A89).
4. Full-width **sparkline** (own row, `margin-top:10px`, height 28px) — a 24h series
   that crawls right-to-left. Line 1.6px in the health color, area fill at ~8% alpha.

The three tiles (exact content in healthy state):
- **TPOT p99 · blended** — `42 ms / SLO 60ms`, sub `42ms headroom to SLO`, delta `▼ 3ms vs 24h`.
- **Cost at SLO** — `$0.83 / 1M tok`, sub `blended across both pools at current mix`, delta `▼ 6% vs 24h`.
- **MTTR · rolling** — `47 s`, sub `agent detect→resolve · manual baseline 148s`, delta `▼ 68% vs manual` (teal).

### 3. SLO Panel
Fills the remaining fold height. `#0E141B` card, 10px radius, `padding:16px 18px`.
`display:grid; grid-template-columns:1fr 340px; gap:22px`.

**Left — live latency distributions.** Header `LATENCY SLO · live distribution` +
`TTFT ≤ 300ms · TPOT ≤ 60ms`. A `1fr 1fr` grid, one column per pool
(**Baseten-A100** / **vLLM-L4**). Each pool column:
- Pool header: 8px square accent chip + pool name (Inter 600, 12.5px) + model name
  (JetBrains Mono 500, 10.5px, #5C6A78) + status word right-aligned (HEALTHY teal /
  DEGRADED amber / EJECTED red, Inter 600, 9.5px, UPPERCASE).
- Two **distribution strips** (TTFT, then TPOT). Each strip is an SVG (viewBox 0 0 272 44):
  a smooth right-skewed **density curve** (area path, stroke 1.2px in #5AB0FF, fill tinted
  by breach state), a dotted p50 marker (#93A1B0), a solid p99 marker (health-colored),
  and a **red dashed SLO threshold line**. This is *not* a bar chart — it is a density
  strip against the SLO line. Below it: `p50 / p95 / p99` values in JetBrains Mono 10px,
  p99 colored by breach.
- A short readout right of the metric label: `within SLO` / `near SLO` / `p99 over SLO`.

**Right — Goodput × Concurrency.** Header `GOODPUT × CONCURRENCY` + `req/s meeting SLO ·
operating point live`. SVG (viewBox 0 0 320 190): axes in #1C2530, a Rayleigh-shaped curve
(teal 2px) that rises to a knee then rolls off, a faint dashed vertical at the peak, and a
**live operating-point dot** (r 4.5, teal when left of knee, amber when past it) with a
dashed guide. Caption: `op · <N> concurrent · <M>% peak goodput` and a note
`left of knee — headroom available` / `past the knee — goodput rolling off`.

### 4. Placement Map (below fold)
Header `PLACEMENT MAP · router decisions · reason-annotated`.
`display:grid; grid-template-columns:1fr 360px 1fr; gap:14px`.

**Left & right — pool cards.** `#0E141B`, 10px radius, `padding:16px 18px`. Border tints
by state (red #3A1A1D when ejected, amber #3A2E12 when degraded, else #1C2530). Contents:
- Header: pool name (Inter 600, 14px) + `model · region` sub; status badge (pill, tinted bg).
- 3-col metric row: **Util** (24px number, %, colored: teal / amber >90 / red ejected),
  **Health** score (24px), **$/1M tok** (24px).
- Replica bar: `Replicas 12/12` label + `<util>% load`; 6px track (#161E27) with a fill
  bar in the util color (`transition: width .4s`).
- A faint util sparkline (26px).

**Center — decision feed + connector.** `#0B1016` card. At top: a 1px horizontal connector
line with **request dots** that traverse it left↔right (`transition: left .3s linear`,
8px, glowing, colored by target pool / amber during incident). Below: header
`PLACEMENT DECISIONS` + a scrolling column (max-height 320px, custom 6px scrollbar) of
decision rows, newest on top with a `dvFeedIn .35s` entrance. Each row:
`#8258  voice/compliance-EU → baseten-a100      10ms` on line 1, and
`reason · affinity: kv-cache` on line 2. Newest row has a lighter bg (#141C25) + brighter border.

### 5. Release + Incident lane (below fold)
`display:grid; grid-template-columns:340px 1fr; gap:14px`.

**Left — Canary Release card.** Header `CANARY RELEASE` + subject
`Qwen3-8B → v2.4.1 · pool vllm-l4`. A **vertical 1%→10%→50%→100% stepper**: each step a
node (11px circle, filled/teal when passed, ring when running, connector line between) +
percent label + verdict word (PASS teal / RUNNING teal / PAUSED|HELD amber / QUEUED grey).
Below: an **SLO gate** box (tinted bg + border) with the current gate verdict text.

**Right — Incidents.** `display:grid; grid-template-columns:1fr 300px; gap:22px`.
- Header `INCIDENTS · agent-driven · detect → diagnose → resolve` + a right-aligned
  `MTTR 30d avg 47s · ▼68% vs manual`.
- **Incident card(s):** title + status dot (pulsing red `dvPulse 1.4s` while active,
  teal when resolved) + **MTTR badge** (pill). A one-line technical narrative. Then a
  **duration bar**: three segments (detect / diagnose / resolve) whose *widths* are
  proportional to their durations (6s : 8s : 33s) and whose *inner fills* animate in real
  time as the incident progresses (amber / amber-dark / teal). Segment labels below.
  Then an **agent-action log**: timestamped rows (`+0s`, `+6s`, …) that light up as their
  timestamp passes (dim → bright, dot amber→teal). Footer: `→ auto-postmortem PM-2291`
  link + rollback note.
- **MTTR history chart (300×170 SVG):** two polylines — **manual** baseline (dashed grey,
  ~148s flattish) and **agent** (teal, declining to 47s) — with the **gap between them
  shaded** teal@9% (time saved per incident).

---

## Required States (dev switcher forces them; production derives from telemetry)
- **(a) Healthy / steady:** all pools within SLO, teal everywhere, TPOT p99 ~42ms,
  cost $0.83, canary at 50% RUNNING, "No active incident" card showing the last resolved one.
- **(b) Degrading:** vLLM-L4 goes **amber/DEGRADED** (util ~93%, TPOT p99 ~59ms), Baseten-A100
  util climbs (~79%) as traffic **rebalances** to it, feed reasons shift to `spill: pool
  saturated`, operating point moves past the knee, canary gate **PAUSED**, hero TPOT ~54ms amber.
- **(c) Live incident:** vLLM-L4 **EJECTED** (util→~4%, health 12, red), traffic **spills**
  to Baseten-A100 (util ~95%), incident card active with **pulsing** dot, MTTR badge
  **counts up in real time**, agent-action log fills, duration bar fills, canary **HELD**.
- **(d) Replay:** a scripted **90-second loop** (this is the state the demo video is recorded in):
  0–14s healthy → 14–28s degrading → 28–75s incident (timeline fills against the real 47s MTTR)
  → 75–90s recovered, then repeats.

## Interactions & Behavior
- **Global tick:** a single 300ms interval drives everything. Each tick eases live metrics
  toward the current state's targets (`v += (target - v) * 0.16`) with small jitter, then
  pushes to fixed-length (48) ring buffers for the sparklines (which therefore *crawl*).
- **Number motion is meaning:** numbers only move because their underlying telemetry moved.
  No decorative animation.
- **Placement feed:** a new decision is prepended every ~3 ticks (~0.9s); list caps at 9;
  each new row spawns a **request dot** that traverses the connector (removed when it
  reaches the far side; max 8 concurrent).
- **Incident timeline** fills from `incidentMs` (real elapsed ms in incident mode; scripted
  offset in replay). Detect completes at 6s, diagnose at 14s, resolve at 47s; each agent
  action appears when elapsed ≥ its timestamp.
- **Switcher:** clicking a state sets the mode immediately; entering INCIDENT resets the
  elapsed counter; entering REPLAY resets the 90s clock.
- Animations: `dvBlink` (status dot, 2.4s), `dvPulse` (active incident dot, 1.4s),
  `dvFeedIn` (new feed row, .35s ease), width transitions .4s on util bars, .3s linear on dots.

## State Management
- `mode`: `'healthy' | 'degrading' | 'incident' | 'replay'` — the only user-set state.
- Derived **effective mode** + elapsed incident ms (replay maps its 90s clock onto healthy/
  degrading/incident phases).
- Live metric store per pool: `util, health, ttft[p50,p95,p99], tpot[p50,p95,p99], cost,
  status, replicas`, plus blended `tpot99, cost, concurrency`.
- Ring buffers (len 48) for hero sparklines (tpot, cost, mttr) and per-pool util.
- Feed array, in-flight dots array, incident elapsed counter, replay clock.
- In production, replace the tick+targets simulation with subscriptions to the feeds below;
  keep the same easing/buffering on the client so charts stay smooth between polls.

## Data Sources (feeds to wire — annotated in the HTML as comments)
- Topbar: `GET /v1/cluster/status` — 2s poll.
- Hero: `GET /v1/slo/rollup` + `/v1/costs` (blended) + `/v1/incidents/mttr` — 5s poll.
- SLO panel: `GET /v1/slo/histograms` per pool (TTFT+TPOT p50/p95/p99) — 2s poll;
  `GET /v1/goodput` curve — 10s poll.
- Placement: `GET /v1/pools` rollup — 2s poll; `/v1/placement/decisions` — **SSE stream**.
- Canary: `GET /v1/releases/active` + gate verdicts — 5s poll.
- Incidents: `GET /v1/incidents` live + `/v1/incidents/mttr` history.

## Design Tokens

**Color**
- Background: `#0A0E12`
- Panel: `#0E141B` · deep panel (feed): `#0B1016` · inset track: `#161E27`
- Borders: `#1C2530` (default) · `#243040` (control) · `#161E27` (hairline) ·
  `#3A1A1D` (red state) · `#3A2E12` (amber state) · `#173029` (teal state)
- Text: primary `#E6EDF3` · secondary `#93A1B0` · body `#8B98A5` · dim `#6B7A89` ·
  faint `#5C6A78` · ghost `#3E4A57`
- **Healthy accent (teal):** `#2FE0C6`
- **Degrading (amber):** `#FFB020` (and `#F5A623` for the diagnose segment)
- **SLO breach (red):** `#FF5257`
- Cost/secondary series (blue): `#5AB0FF`
- Replay accent (violet): `#B08CFF`
- State tints: accent at ~8–14% alpha for chip/badge backgrounds.

**Typography**
- Sans: **Inter** (400/500/600/700). Mono: **JetBrains Mono** (400/500/600).
- Global `font-variant-numeric: tabular-nums`.
- Big hero numeral: Inter 650, 44px, letter-spacing -.025em. Card numbers: 24px.
- Micro-labels: Inter 600, 10.5–11px, letter-spacing .12–.15em, UPPERCASE.
- Mono is used for all IDs, timestamps, ms/$/percent readouts, and code-like tokens.

**Spacing:** strict **8px grid** (12/14/16/18/22px used for gaps and padding).
**Radius:** cards 10px · pills/boxes 5–7px · bars 3px.
**Shadows:** none — depth comes from bg/border steps and glow on live dots
(`box-shadow: 0 0 8px <accent>`).
**Charts:** exactly three chart idioms total — (1) crawling sparklines, (2) SLO density
strips, (3) the goodput + MTTR line charts. No pie/donut charts, no rainbow palettes.

## Mock Data Realism (preserve this vocabulary)
- Real models: **GPT-OSS-120B** (Baseten-A100), **Qwen3-8B** (vLLM-L4).
- Latencies: TTFT 80–400ms, TPOT 18–59ms. Costs $0.61–$1.79 per 1M tok (blended ~$0.83).
- Request IDs like `#8241`, UTC timestamps, decision latencies `8–24ms`.
- Incident narrative (must stay technically coherent): *"Replica stuck after OOM on
  8K-context burst; ejected; traffic spilled to baseten-a100; canary rollback not required."*
  Agent actions: detect breach → correlate OOM kills → eject replicas → spill traffic
  (right-of-way) → scale +2 replicas → SLO recovered. MTTR 47s.

## Files
- `Devboard.dc.html` — the full design reference (all four states, live simulation).
- `support.js` — prototype runtime shim **only** (do not port; lets the HTML open standalone).

To view the reference: open `Devboard.dc.html` in a browser and use the top-right
`DEV` switcher to step through all four states.
