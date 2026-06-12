#!/usr/bin/env python3
"""Write deployed service URLs into routing-policy.yaml's endpoint map.

    terraform -chdir=deploy/terraform/envs/staging output -json \\
        | python3 tools/sync_endpoints.py

Reads terraform outputs (gcp_urls / aws_urls maps keyed by service dir name),
translates service dirs to model names via inference-registry.yaml, and
upserts {provider, url} entries per model — preserving entries it doesn't
own (e.g. local-docker). Providers are derived as
gcp-cloudrun-<target> / aws-apprunner-<target> to match cost_table keys.

Stdlib-only: runs in CI before any pip install. The endpoints section must be
the LAST section of routing-policy.yaml (it is; keep it that way).
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "devkit"))
import registry  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CLOUD_PROVIDERS = {"gcp_urls": "gcp-cloudrun", "aws_urls": "aws-apprunner"}


def parse_endpoints(policy_text: str) -> dict[str, list[dict]]:
    """Parse the endpoints: section into {model: [{provider, url}, ...]}."""
    endpoints: dict[str, list[dict]] = {}
    in_section = False
    model = None
    for raw in policy_text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" "):
            in_section = line.strip() == "endpoints:"
            continue
        if not in_section:
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 2 and stripped.endswith(":"):
            model = stripped[:-1]
            endpoints[model] = []
        elif stripped.startswith("- provider:") and model:
            endpoints[model].append(
                {"provider": stripped.split(":", 1)[1].strip()})
        elif stripped.startswith("url:") and model and endpoints[model]:
            endpoints[model][-1]["url"] = stripped.split(":", 1)[1].strip()
    return endpoints


def render_endpoints(endpoints: dict[str, list[dict]]) -> str:
    lines = ["endpoints:"]
    for model in sorted(endpoints):
        lines.append(f"  {model}:")
        for ep in endpoints[model]:
            lines.append(f"    - provider: {ep['provider']}")
            lines.append(f"      url: {ep['url']}")
    return "\n".join(lines) + "\n"


def merge(policy_path: Path, tf_outputs: dict, repo_root: Path) -> str:
    """Return the updated routing-policy.yaml text."""
    backends = registry.load(repo_root)
    # service dir name -> (model name, target)
    by_dir = {b["path"].split("/")[-1]: (b["name"], b.get("target", "cpu"))
              for b in backends}

    text = policy_path.read_text()
    endpoints = parse_endpoints(text)

    for output_key, provider_base in CLOUD_PROVIDERS.items():
        urls = (tf_outputs.get(output_key) or {}).get("value") or {}
        for service_dir, url in urls.items():
            if service_dir not in by_dir:
                continue  # infrastructure (router) — not a routing target
            model, target = by_dir[service_dir]
            provider = f"{provider_base}-{target}"
            entries = endpoints.setdefault(model, [])
            entries[:] = [e for e in entries if e["provider"] != provider]
            entries.append({"provider": provider, "url": url})

    head = text.split("endpoints:")[0].rstrip("\n")
    return head + "\n\n" + render_endpoints(endpoints)


def main() -> int:
    tf_outputs = json.load(sys.stdin)
    policy_path = REPO_ROOT / "routing-policy.yaml"
    updated = merge(policy_path, tf_outputs, REPO_ROOT)
    policy_path.write_text(updated)
    print(f"updated {policy_path.name} endpoint map from terraform outputs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
