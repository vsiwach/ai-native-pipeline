#!/usr/bin/env python3
"""Build the Modular knowledge-base index (sqlite FTS5) from public sources.

Sources (all public):
  - docs.modular.com   (MAX, Mojo, Mammoth docs — via sitemap)
  - modular.com/blog   (announcements, changelog posts)
  - the modular skills repo READMEs / SKILL.md files (local checkout path)

Design choices, deliberately boring:
  - stdlib only (urllib + sqlite3 + html.parser): runs anywhere the repo runs.
  - BM25 via sqlite FTS5 — no embedding service inside the perimeter, nothing
    to GPU-host for retrieval; the LLM does synthesis, the index does recall.
  - Chunks ~1200 chars with 150 overlap, keyed by URL fragment.

Usage:
  python3 tools/ragindex/build_index.py --out services/docs_assist/kb/modular_kb.sqlite \
      [--skills-repo /path/to/modular-skills] [--max-pages 400] [--offline-dir DIR]

--offline-dir ingests pre-downloaded .html/.md files instead of crawling
(useful in CI and for reproducible index hashes).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sqlite3
import sys
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

UA = {"User-Agent": "docs-assist-indexer/0.1 (unofficial demo; public docs only)"}
SITEMAPS = ["https://docs.modular.com/sitemap.xml", "https://www.modular.com/sitemap.xml"]
ALLOW = re.compile(r"https://(docs\.modular\.com|www\.modular\.com/blog)")


class _Text(HTMLParser):
    SKIP = {"script", "style", "nav", "footer", "header"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self.title = ""
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> tuple[str, str]:
    p = _Text()
    p.feed(html)
    text = re.sub(r"\s+", " ", " ".join(p.parts)).strip()
    return p.title.strip() or "untitled", text


def chunk(text: str, size: int = 1200, overlap: int = 150):
    i = 0
    while i < len(text):
        yield text[i : i + size]
        i += size - overlap


def fetch(url: str, timeout: int = 20) -> str:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def sitemap_urls(max_pages: int) -> list[str]:
    urls: list[str] = []
    for sm in SITEMAPS:
        try:
            root = ElementTree.fromstring(fetch(sm))
        except Exception as e:  # noqa: BLE001 — a missing sitemap is survivable
            print(f"warn: sitemap {sm}: {e}", file=sys.stderr)
            continue
        for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            u = (loc.text or "").strip()
            if ALLOW.match(u):
                urls.append(u)
    return urls[:max_pages]


def make_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE VIRTUAL TABLE chunks USING fts5(doc_id, url, title, text, tokenize='porter')"
    )
    conn.execute("CREATE TABLE meta (k TEXT PRIMARY KEY, v TEXT)")
    return conn


def ingest(conn: sqlite3.Connection, url: str, title: str, text: str) -> int:
    n = 0
    for j, c in enumerate(chunk(text)):
        if len(c.strip()) < 200:
            continue
        conn.execute(
            "INSERT INTO chunks (doc_id, url, title, text) VALUES (?,?,?,?)",
            (f"{hashlib.sha256(url.encode()).hexdigest()[:12]}:{j}", url, title, c),
        )
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="services/docs_assist/kb/modular_kb.sqlite")
    ap.add_argument("--skills-repo", default=None, help="local checkout of modular's skills repo")
    ap.add_argument("--offline-dir", default=None, help="ingest local .html/.md instead of crawling")
    ap.add_argument("--max-pages", type=int, default=400)
    ap.add_argument("--delay", type=float, default=0.4, help="politeness delay between fetches")
    args = ap.parse_args()

    conn = make_db(Path(args.out))
    total = 0

    if args.offline_dir:
        for f in sorted(Path(args.offline_dir).rglob("*")):
            if f.suffix == ".html":
                title, text = html_to_text(f.read_text("utf-8", "replace"))
                total += ingest(conn, f"file://{f}", title, text)
            elif f.suffix in (".md", ".mdx"):
                total += ingest(conn, f"file://{f}", f.stem, f.read_text("utf-8", "replace"))
    else:
        for u in sitemap_urls(args.max_pages):
            try:
                title, text = html_to_text(fetch(u))
                total += ingest(conn, u, title, text)
                time.sleep(args.delay)
            except Exception as e:  # noqa: BLE001
                print(f"warn: {u}: {e}", file=sys.stderr)

    if args.skills_repo:
        for f in sorted(Path(args.skills_repo).rglob("*.md")):
            total += ingest(conn, f"skills://{f.name}", f"skill: {f.stem}", f.read_text("utf-8", "replace"))

    conn.execute("INSERT INTO meta VALUES ('built_at', ?)", (time.strftime("%Y-%m-%dT%H:%M:%SZ"),))
    conn.commit()
    digest = hashlib.sha256(Path(args.out).read_bytes()).hexdigest()
    conn.execute("INSERT INTO meta VALUES ('note', 'unofficial demo index of public Modular docs')")
    conn.commit()
    conn.close()
    print(f"indexed {total} chunks -> {args.out}\nindex sha256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
