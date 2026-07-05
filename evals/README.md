# Eval set — docs-assist route (customer custody)

`docs_qa.jsonl` is the seed (12 items). Grow it to ~150 with
`python3 tools/ragindex/suggest_evals.py` (generates candidate Q&A from the
built index for human curation) before any certification you show anyone.

Each item: `question`, `must_include` (keyword rubric, all lowercase),
`must_not_include`. Grounding (citations present) is checked automatically
by the certifier on every item — the rubric is the second gate.

Custody model: this file's sha256 is embedded in every certification record.
In a real engagement the file lives in the CUSTOMER's repo; here it lives
with the demo, clearly labeled. Update the seeds against the live index —
facts must match what the public docs actually say at index-build time.
