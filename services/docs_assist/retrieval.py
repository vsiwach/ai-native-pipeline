"""BM25 retrieval over the Modular knowledge base (sqlite FTS5, stdlib-only).

The index is built by tools/ragindex/build_index.py. This module is the
runtime read path: query -> top-k chunks with source URLs, used to ground
every docs-assist answer. Grounding is what makes answers *certifiable*:
the certifier checks each answer cites at least one retrieved chunk.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

DEFAULT_INDEX = Path(__file__).parent / "kb" / "modular_kb.sqlite"


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    url: str
    title: str
    text: str
    score: float


def _fts_query(raw: str) -> str:
    """Sanitize a user question into an FTS5 OR-query of bare terms."""
    terms = re.findall(r"[A-Za-z0-9_.+-]{2,}", raw.lower())
    if not terms:
        return '""'
    return " OR ".join(f'"{t}"' for t in terms[:24])


class Retriever:
    def __init__(self, index_path: Path | str = DEFAULT_INDEX):
        self.index_path = Path(index_path)
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"KB index not found at {self.index_path}. "
                "Run: python3 tools/ragindex/build_index.py"
            )
        self._conn = sqlite3.connect(f"file:{self.index_path}?mode=ro", uri=True,
                                     check_same_thread=False)

    def search(self, query: str, k: int = 4) -> list[Chunk]:
        sql = (
            "SELECT doc_id, url, title, text, bm25(chunks) AS rank "
            "FROM chunks WHERE chunks MATCH ? ORDER BY rank LIMIT ?"
        )
        rows = self._conn.execute(sql, (_fts_query(query), k)).fetchall()
        return [Chunk(doc_id=r[0], url=r[1], title=r[2], text=r[3], score=-float(r[4]))
                for r in rows]

    def close(self) -> None:
        self._conn.close()


def build_context(chunks: list[Chunk], budget_chars: int = 6000) -> str:
    """Render retrieved chunks into the system-prompt context block."""
    parts, used = [], 0
    for i, c in enumerate(chunks, 1):
        block = f"[{i}] {c.title} — {c.url}\n{c.text.strip()}\n"
        if used + len(block) > budget_chars:
            break
        parts.append(block)
        used += len(block)
    return "\n".join(parts)
