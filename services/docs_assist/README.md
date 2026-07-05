# docs-assist

Retrieval-grounded docs agent — the certified-migration demo route. An
OpenAI-compatible proxy: each `/v1/chat/completions` request retrieves top-k
chunks from the local KB index (sqlite FTS5, BM25), injects them as grounded
system context, forwards to `UPSTREAM_BASE_URL` (MAX / vLLM pod, frontier
API, or the repo's llm-sim), and streams the answer back with citation
metadata headers (`X-Citations`, `X-Retrieval-Ms`).

Grounding is what makes answers *certifiable*: `tools/certify.py` checks
each shadow-logged answer cites at least one retrieved chunk before a route
can be promoted.

## Endpoints
- `GET /healthz` — degraded until the KB index exists
- `GET /v1/info` — model, upstream, KB path, demo disclosure
- `POST /v1/chat/completions` — streaming + non-streaming, OpenAI-compatible

## Env
| Var | Default | Meaning |
|---|---|---|
| `UPSTREAM_BASE_URL` | `http://localhost:8000/v1` | OpenAI-compatible generation endpoint |
| `UPSTREAM_MODEL` | `Qwen/Qwen2.5-14B-Instruct` | model name sent upstream |
| `UPSTREAM_API_KEY` | (empty) | bearer for frontier pass-through |
| `KB_INDEX` | `<pkg>/kb/modular_kb.sqlite` | FTS5 index path |

## Build the KB
    python3 tools/ragindex/build_index.py --out services/docs_assist/kb/modular_kb.sqlite

## Run locally
    KB_INDEX=services/docs_assist/kb/modular_kb.sqlite \
    UPSTREAM_BASE_URL=http://127.0.0.1:8111/v1 \
    uvicorn app:app --app-dir services/docs_assist --port 8112

Tests: `python3 -m unittest discover -s services/docs_assist/tests` (or Bazel).
