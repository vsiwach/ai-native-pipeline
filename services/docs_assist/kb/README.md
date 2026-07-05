# KB index (built artifact — not committed)

`modular_kb.sqlite` (sqlite FTS5) lands here. Build it with:

    python3 tools/ragindex/build_index.py --out services/docs_assist/kb/modular_kb.sqlite

Online mode crawls the public docs sitemap; `--offline-dir DIR` ingests
pre-downloaded `.html`/`.md` files for reproducible index hashes (CI, or
when the network is unavailable). The index sha256 is printed on build and
belongs in any certification record that used it.
