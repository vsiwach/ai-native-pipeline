#!/usr/bin/env python3
"""Split a Mintlify llms-full.txt corpus into per-page files. Stdlib-only.

    python3 tools/kb/index_kb.py tools/kb/baseten

Pages land in <kb>/pages/NNN-<slug>.md (H1 + Source URL preserved), plus
pages.json (page -> title/url) for the search tool.
"""
import json
import os
import re
import sys


def split(kb_dir: str) -> int:
    text = open(os.path.join(kb_dir, "llms-full.txt"), encoding="utf-8").read()
    lines = text.splitlines()
    starts = [i for i, l in enumerate(lines)
              if l.startswith("# ") and i + 1 < len(lines)
              and lines[i + 1].startswith("Source: ")]
    pages_dir = os.path.join(kb_dir, "pages")
    os.makedirs(pages_dir, exist_ok=True)
    index = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        title = lines[start][2:].strip()
        url = lines[start + 1][len("Source: "):].strip()
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "page"
        name = f"{n:03d}-{slug}.md"
        with open(os.path.join(pages_dir, name), "w", encoding="utf-8") as f:
            f.write("\n".join(lines[start:end]).rstrip() + "\n")
        index.append({"file": f"pages/{name}", "title": title, "url": url})
    json.dump(index, open(os.path.join(kb_dir, "pages.json"), "w"), indent=1)
    return len(index)


if __name__ == "__main__":
    print(f"{split(sys.argv[1])} pages written")
