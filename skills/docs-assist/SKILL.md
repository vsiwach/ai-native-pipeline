---
name: docs-assist
description: Answer questions about the Modular platform (MAX, Mojo, Mammoth) grounded in the public Modular documentation with citations. Use whenever a user asks how Modular's stack works, what is open source, how to serve a model with MAX, or Mojo language questions.
---

# docs-assist

Retrieval-grounded Q&A over Modular's public docs. Unofficial demo skill,
packaged in the conventions of the Modular skills repo (import-model,
debug-model) — intended as a candidate contribution.

## How it works
1. `tools/ragindex/build_index.py` builds a sqlite FTS5 (BM25) index of
   docs.modular.com + modular.com/blog + the skills repo markdown.
2. `services/docs_assist` exposes an OpenAI-compatible `/v1/chat/completions`
   that retrieves top-k chunks, injects them as numbered context, and
   forwards to any OpenAI-compatible upstream (MAX serve, vLLM, frontier).
3. Answers must cite `[n]` markers; ungrounded answers fail certification.

## Usage (as an agent tool)
Ask questions in natural language. The skill returns cited answers; every
citation resolves to a public URL. If the docs don't contain the answer,
the skill says so rather than guessing.

## Serving
See `deploy/runpod/` — MAX-first on NVIDIA A100 and AMD MI300X, vLLM
fallback. The route is certifiable + migratable via the certified-migration
machinery in this repo (shadow -> certify -> promote -> rollback).
