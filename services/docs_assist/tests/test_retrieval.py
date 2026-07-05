"""Retrieval smoke tests — runnable under plain python3 (repo convention)."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from retrieval import Retriever, build_context  # noqa: E402


def make_index(path):
    conn = sqlite3.connect(path)
    conn.execute("CREATE VIRTUAL TABLE chunks USING fts5(doc_id, url, title, text, tokenize='porter')")
    rows = [
        ("a:0", "https://docs.modular.com/max", "MAX intro",
         "MAX is Modular's serving framework. The MAX framework and serving layer are "
         "open source under the Apache 2.0 license, self-hostable on a single node."),
        ("b:0", "https://docs.modular.com/mojo", "Mojo FAQ",
         "Mojo is a systems programming language. The Mojo compiler ships open source "
         "Apache 2.0 in fall 2026; the stdlib and kernels are already open."),
        ("c:0", "https://docs.modular.com/mammoth", "Mammoth",
         "Mammoth is the commercial control plane for fleet operations, KV-aware "
         "routing and disaggregated serving across NVIDIA and AMD hardware pools."),
    ]
    conn.executemany("INSERT INTO chunks VALUES (?,?,?,?)", rows)
    conn.commit()
    conn.close()


class TestRetrieval(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.idx = Path(self.tmp.name) / "kb.sqlite"
        make_index(self.idx)

    def test_top_hit_is_relevant(self):
        r = Retriever(self.idx)
        hits = r.search("what license is the Mojo compiler under?", k=2)
        self.assertTrue(hits and "mojo" in hits[0].url)

    def test_context_is_numbered_and_cited(self):
        r = Retriever(self.idx)
        ctx = build_context(r.search("KV-aware routing control plane", k=3))
        self.assertIn("[1]", ctx)
        self.assertIn("https://docs.modular.com", ctx)

    def test_missing_index_raises(self):
        with self.assertRaises(FileNotFoundError):
            Retriever(Path(self.tmp.name) / "nope.sqlite")


if __name__ == "__main__":
    unittest.main()
