# PHASE 5 — Developer dashboard (UX)

Paste everything below into Claude Code.

---

Build `tools/devboard/` — a single-page developer dashboard for this pipeline.
Audience: engineers on the team. It must feel calm and information-dense, in the
spirit of Anthropic/Claude design language.

## Design system (follow strictly)
- Single HTML file + React via CDN (no build step) OR Vite if you prefer — but
  zero backend: it talks directly to the GitHub API and the router's /v1/costs.
- Palette: warm neutrals — background #FAF9F5, ink #141413, muted #6E6E64,
  accent (sparingly) #D97757; success #2E7D4F, fail #C0392B.
- Type: system serif for headings (Georgia fallback), system sans for data.
- Layout: 12-col grid, generous whitespace, no drop shadows, 1px hairline borders
  (#E8E6DD), rounded-lg. Dark mode via prefers-color-scheme.
- Empty/loading/error states designed, not an afterthought. No spinners >300ms
  without a skeleton.

## Panels
1. **Pipeline** — latest CI runs on main + open PRs (GitHub REST, PAT pasted into
   a settings drawer, stored in memory only — never localStorage the token).
   Each run: status dot, name, sha, relative time, link.
2. **Deployments** — recent GitHub Deployments per environment with cloud badge
   (gcp/aws), and a "Deploy staging" button that fires the workflow_dispatch —
   confirm dialog quotes the governance policy line it's invoking.
3. **Inference economics** — poll router `/v1/costs`: per-backend request counts,
   est. spend, cache hit rate; tiny sparkline per backend (inline SVG, no chart lib).
4. **Agent activity** — merged PRs with `[agent:*]` trailers (last 14 days), the
   agent-authored share %, human-edit rate — same definitions as metrics/dora.py.

## Tasks
1. Build it, mobile-responsive, accessible (focus rings, aria labels, contrast AA).
2. A `tools/devboard/README.md` with a screenshot and 3-line setup.
3. Serve locally via `python3 -m http.server` — document the one-liner.

## Acceptance criteria
- Loads with no console errors; all four panels render with mocked data when no
  token is set (ship a `mock=true` query param), real data when token provided
- Deploy button → workflow_dispatch fires (verify in Actions tab) and the
  confirm dialog shows the policy citation
- Lighthouse accessibility score ≥ 95 (show the run)
