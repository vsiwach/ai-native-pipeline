#!/usr/bin/env python3
"""Emit inference-registry.yaml as JSON for the CI build matrix.

    python3 tools/registry_json.py            # full entries
    python3 tools/registry_json.py --names    # just backend names

containers.yml consumes this via fromJSON so adding a backend to the registry
never requires editing the workflow.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "devkit"))
import registry  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    backends = registry.load(REPO_ROOT)
    problems = registry.validate(REPO_ROOT)
    if problems:
        for p in problems:
            print(f"registry invalid: {p}", file=sys.stderr)
        return 1
    if "--names" in sys.argv:
        print(json.dumps([b["name"] for b in backends]))
    else:
        print(json.dumps(backends))
    return 0


if __name__ == "__main__":
    sys.exit(main())
