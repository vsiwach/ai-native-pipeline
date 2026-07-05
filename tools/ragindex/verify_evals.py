#!/usr/bin/env python3
"""Verify eval facts against the built KB index (Phase 6 task D).

For every item in evals/docs_qa.jsonl:
  - retrieve top-k chunks for the question (the same recall path the agent
    uses at serve time);
  - check each must_include keyword appears in those chunks (RETRIEVED),
    else anywhere in the corpus (IN_CORPUS — the fact exists but recall
    missed it at this k), else nowhere (MISSING — the rubric asserts
    something the docs don't say; fix the eval, never the docs).

Exit 0 when every keyword is at least IN_CORPUS; 1 when anything is
MISSING. Writes a JSON report next to the evals for provenance.

Usage:
  python3 tools/ragindex/verify_evals.py \
      --index services/docs_assist/kb/modular_kb.sqlite \
      --evals evals/docs_qa.jsonl --k 8 \
      --report evals/docs_qa.verification.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]
                       / "services" / "docs_assist"))
from retrieval import Retriever  # noqa: E402


def in_corpus(conn: sqlite3.Connection, needle: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM chunks WHERE lower(text) LIKE ? LIMIT 1",
        (f"%{needle.lower()}%",)).fetchone()
    return row is not None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index",
                    default="services/docs_assist/kb/modular_kb.sqlite")
    ap.add_argument("--evals", default="evals/docs_qa.jsonl")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--report", default="evals/docs_qa.verification.json")
    args = ap.parse_args()

    retriever = Retriever(args.index)
    conn = sqlite3.connect(f"file:{args.index}?mode=ro", uri=True)
    items = [json.loads(l)
             for l in Path(args.evals).read_text().splitlines() if l.strip()]

    rows, missing = [], 0
    for item in items:
        hits = retriever.search(item["question"], k=args.k)
        blob = " ".join(c.text.lower() for c in hits)
        keywords = []
        for kw in item.get("must_include", []):
            if kw.lower() in blob:
                status = "RETRIEVED"
            elif in_corpus(conn, kw):
                status = "IN_CORPUS"
            else:
                status = "MISSING"
                missing += 1
            keywords.append({"keyword": kw, "status": status})
        worst = ("MISSING" if any(k["status"] == "MISSING" for k in keywords)
                 else "IN_CORPUS" if any(k["status"] == "IN_CORPUS"
                                         for k in keywords)
                 else "RETRIEVED" if keywords else "NO_KEYWORDS")
        rows.append({"id": item["id"], "question": item["question"],
                     "keywords": keywords, "status": worst,
                     "top_urls": [c.url for c in hits[:3]]})
        print(f"{item['id']}  {worst:10}  {item['question'][:70]}")
        for k in keywords:
            if k["status"] != "RETRIEVED":
                print(f"      !! {k['status']}: {k['keyword']!r}")

    report = {
        "kind": "modular-demo/eval-verification",
        "index": args.index,
        "index_sha256": __import__("hashlib").sha256(
            Path(args.index).read_bytes()).hexdigest(),
        "evals": args.evals,
        "k": args.k,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "items": rows,
    }
    Path(args.report).write_text(json.dumps(report, indent=2))
    print(f"\n{len(items)} items; {missing} keyword(s) MISSING "
          f"-> {args.report}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
