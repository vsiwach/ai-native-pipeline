#!/usr/bin/env python3
"""Generate candidate eval Q&A from the built KB index, for human curation.

Pulls high-signal chunks (titles containing FAQ/overview/get started) and
emits template questions with the source URL so a human can write the
must_include rubric against what the docs actually say. Never auto-commits
facts — curation is the custody step.

Usage: python3 tools/ragindex/suggest_evals.py --index services/docs_assist/kb/modular_kb.sqlite --n 60
"""
from __future__ import annotations

import argparse
import json
import sqlite3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="services/docs_assist/kb/modular_kb.sqlite")
    ap.add_argument("--n", type=int, default=60)
    args = ap.parse_args()
    conn = sqlite3.connect(args.index)
    rows = conn.execute(
        "SELECT DISTINCT title, url FROM chunks WHERE title LIKE '%FAQ%' "
        "OR title LIKE '%overview%' OR title LIKE '%Get started%' "
        "OR title LIKE '%intro%' LIMIT ?", (args.n,)).fetchall()
    for i, (title, url) in enumerate(rows, 100):
        print(json.dumps({
            "id": f"q{i}",
            "question": f"TODO: write a question answerable from: {title}",
            "must_include": ["TODO"],
            "must_not_include": [],
            "source": url,
        }))


if __name__ == "__main__":
    main()
