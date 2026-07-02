# Benchmarks — the provenance chain

Every latency/cost number shown anywhere (devboard, docs, README tables)
must trace to a raw per-request CSV in `benchmarks/raw/`, written by
`harness.py` and aggregated by `summarize.py`. SLO-AUDITOR re-runs these
commands and rejects anything it can't reproduce.

## Commands

```bash
# stack (sim, $0): docker compose up --build   — or three local uvicorns
# steady load:
python3 benchmarks/harness.py --router http://localhost:8090 \
    --model qwen3-8b --concurrency 6 --duration 25 --label sim-baseline-steady

# goodput sweep + devboard curve artifact:
python3 benchmarks/harness.py --router http://localhost:8090 \
    --model qwen3-8b --sweep 2,4,8,16 --duration 12 --label sim-baseline-sweep
python3 benchmarks/summarize.py --goodput-out benchmarks/goodput.json \
    'benchmarks/raw/sim-baseline-sweep-c*.csv'

# summary table (per pool: TTFT/TPOT p50/p95/p99, goodput@SLO, $/1M tok):
python3 benchmarks/summarize.py 'benchmarks/raw/sim-baseline-steady-*.csv'
```

## Measurement model
- Harness streams every request and measures CLIENT-side TTFT/decode
  (wall clock through the router — the number a user would feel).
- Server-reported economics (X-TTFT-Ms, X-Decode-Ms, X-Est-Cost, token
  counts) ride response headers when the backend provides them; TPOT =
  decode_ms / completion_tokens, falling back to client-measured decode
  over SSE chunk count for live streams.
- Voice SLO (mission): TTFT p99 < 500ms, TPOT p99 < 60ms. Goodput = SLO-
  passing requests per second.
- `--sweep` writes one CSV per concurrency step; the goodput curve
  artifact (`benchmarks/goodput.json`) is what `/v1/metrics/slo` serves —
  the devboard never renders a synthesized curve.

## Labels
`sim-baseline-*` = local simulator pools (no keys/GPU; deterministic
economics). Live-pool baselines (F1) get `live-baseline-*` labels during
the joint deploy session — never compare across the two without saying so.
