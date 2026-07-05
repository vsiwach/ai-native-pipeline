# Certified Migration MVP — docs-assist on real NVIDIA + AMD

The PRD's §9 MVP made real: shadow → certify → promote → rollback on a
retrieval-grounded **Modular docs agent**, served by **MAX** on rented
**A100 (NVIDIA)** and **MI300X (AMD)** pools, with signed parity
certificates and measured — never estimated — costs.

    replayer/chat ─► router ─► frontier (incumbent, customer key)
                       │ shadow ─► docs-assist ─► MAX @ A100  (act 1)
                       │ place  ─► docs-assist ─► MAX @ MI300X (act 2)
                       └─ ledger /v1/costs ─► vercel-deploy/demo.html
    certifier: evals(sha256) + shadow log + bench SLO ─► signed cert ─► gates promote

## What's in this drop
| Path | What | Status |
|---|---|---|
| `services/docs_assist/` | RAG agent service (OpenAI-compatible, SSE, citations) | code + tests green |
| `tools/ragindex/` | KB index builder (public docs, sqlite FTS5) + eval suggester | code |
| `services/router/router_app/shadow.py` | async shadow mirror | code |
| `tools/certify.py` | grounding+rubric scoring, ed25519-signed certs, verify | tested e2e |
| `tools/bench.py` | $/Mtok at fixed SLO (TTFT/TPOT p99), rerunnable reports | code |
| `tools/replay.py` | timed traffic replay through the router | code |
| `evals/docs_qa.jsonl` | seed eval set (12) — grow to ~150, verify facts vs live docs | seed |
| `deploy/runpod/` | pod launch + MAX-first / vLLM-fallback serve scripts | code |
| `skills/docs-assist/SKILL.md` | skill packaged in Modular skills-repo conventions | done |
| `vercel-deploy/demo.html` | demo console: chat + pools + cert + ledger (`?mock=true` works now) | done |
| `PHASE_6_certified_migration.md` | Claude Code integration prompt (router wiring, ./dev, tests) | ready |

## Build plan (~8 days)
| Day | Work |
|---|---|
| 1 | Run PHASE_6 in Claude Code: registry sync, router wiring, SSE, /v1/costs |
| 2 | Build KB index against live docs; curate evals to ~150 (fix seed facts!) |
| 3 | Launch A100 pod; MAX bring-up (use Modular's import-model/debug-model skills — save transcript); bench |
| 4 | Launch MI300X pod; MAX bring-up (vLLM fallback if needed); bench |
| 5 | End-to-end act 1: replay → shadow → certify → promote; fix gaps |
| 6 | End-to-end act 2: NVIDIA→AMD placement + cert; rollback drill |
| 7 | Demo polish: console live-mode, rehearse 3-act script, record backup video |
| 8 | Buffer + PR of skills/docs-assist to Modular's skills repo |

## Demo script (4 min)
1. **Baseline** — route on frontier; ask the agent a question live; chip shows FRONTIER + cost.
2. **Act 1** — replay traffic (shadow fills), show signed cert (`certify verify` on stage), promote; ask again — chip shows A100, ~−60–90% cost, same cited answer.
3. **Act 2** — bench panel A100 vs MI300X ($/Mtok measured at SLO); placement moves route; ask again — chip shows MI300X. One-click rollback to close.

## Honesty rules (do not break these on stage)
- Every $/Mtok = declared pod $/hr ÷ measured tok/s. Both shown.
- Mock mode is labeled MOCK MODE. Never present mock numbers as measured.
- Seed eval facts MUST be re-verified against the live docs index before
  any certification you show (e.g. license/dates claims).
- Frontier $/Mtok varies by provider/model — enter the real price you pay.
- The agent self-describes as an unofficial demo on public docs.

## Budget
A100 ~$1.2–1.9/hr + MI300X (RunPod lists ~$0.5–2.5/hr; confirm in console)
× ~20 pod-hours ≈ **$30–90**. Stop pods between sessions.
