#!/usr/bin/env python3
"""Keyword search over a split KB (see index_kb.py). Stdlib-only.

    python3 tools/kb/search.py tools/kb/baseten "trt-llm quantization fp8" [-n 8]

Scores pages by term frequency (title hits weighted 5x), prints the top
matches with the best-matching snippet — enough to know which page to Read.
"""
import json
import os
import re
import sys


def search(kb_dir: str, query: str, top: int = 8):
    terms = [t for t in re.split(r"[^a-z0-9.+_-]+", query.lower()) if t]
    index = json.load(open(os.path.join(kb_dir, "pages.json")))
    scored = []
    for page in index:
        body = open(os.path.join(kb_dir, page["file"]), encoding="utf-8").read()
        low = body.lower()
        title = page["title"].lower()
        score = sum(low.count(t) + 5 * title.count(t) for t in terms)
        if score:
            # best snippet: first line containing the most terms
            best, best_hits = "", 0
            for line in body.splitlines():
                hits = sum(1 for t in terms if t in line.lower())
                if hits > best_hits:
                    best, best_hits = line.strip(), hits
            scored.append((score, page, best))
    scored.sort(key=lambda s: -s[0])
    return scored[:top]


if __name__ == "__main__":
    kb, query = sys.argv[1], sys.argv[2]
    top = int(sys.argv[sys.argv.index("-n") + 1]) if "-n" in sys.argv else 8
    for score, page, snippet in search(kb, query, top):
        print(f"[{score:4d}] {page['file']}\n       {page['title']} — {page['url']}\n       {snippet[:160]}")
