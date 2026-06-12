"""Read/write inference-registry.yaml without PyYAML.

The registry is intentionally a flat, simple format so a stdlib parser is safe:

    backends:
      house-price-reg:
        path: services/inference
        tier: standard        # realtime | standard | batch
        target: cpu           # cpu | gpu
        max_replicas: 3
        scale_to_zero: true

Only this shape is supported; anything fancier should go through a real YAML
library inside a service's own tooling, not here.
"""

from pathlib import Path

VALID_TIERS = ("realtime", "standard", "batch")
VALID_TARGETS = ("cpu", "gpu")

REGISTRY_HEADER = (
    "# Backend registry — the router reads this; never hard-code routing.\n"
    "# Managed by `./dev new service`, hand-edits welcome.\n"
    "backends:\n"
)


def registry_path(repo_root: Path) -> Path:
    return repo_root / "inference-registry.yaml"


def load(repo_root: Path) -> list[dict]:
    """Return backend entries as dicts (mapping key becomes 'name').

    Missing file -> empty list.
    """
    path = registry_path(repo_root)
    if not path.exists():
        return []
    backends: list[dict] = []
    current: dict | None = None
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip() or line.strip() == "backends:":
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 2 and stripped.endswith(":"):
            current = {"name": stripped[:-1].strip()}
            backends.append(current)
        elif indent >= 4 and ":" in stripped and current is not None:
            key, _, value = stripped.partition(":")
            current[key.strip()] = value.strip().strip("'\"")
    return backends


def add(repo_root: Path, name: str, tier: str, target: str, path: str,
        max_replicas: int = 3, scale_to_zero: bool = True) -> None:
    """Append a backend entry, creating the registry file if needed."""
    if tier not in VALID_TIERS:
        raise ValueError(f"tier must be one of {VALID_TIERS}, got {tier!r}")
    if target not in VALID_TARGETS:
        raise ValueError(f"target must be one of {VALID_TARGETS}, got {target!r}")
    if any(b.get("name") == name for b in load(repo_root)):
        raise ValueError(f"backend {name!r} already registered")
    reg = registry_path(repo_root)
    text = reg.read_text() if reg.exists() else REGISTRY_HEADER
    if not text.endswith("\n"):
        text += "\n"
    text += (
        f"  {name}:\n"
        f"    path: {path}\n"
        f"    tier: {tier}\n"
        f"    target: {target}\n"
        f"    max_replicas: {max_replicas}\n"
        f"    scale_to_zero: {'true' if scale_to_zero else 'false'}\n"
    )
    reg.write_text(text)


def validate(repo_root: Path) -> list[str]:
    """Return a list of problems (empty list = healthy)."""
    problems: list[str] = []
    backends = load(repo_root)
    seen: set[str] = set()
    for i, b in enumerate(backends):
        label = b.get("name", f"entry #{i + 1}")
        for field in ("name", "tier", "target", "path"):
            if not b.get(field):
                problems.append(f"{label}: missing required field '{field}'")
        if b.get("name") in seen:
            problems.append(f"{label}: duplicate backend name")
        seen.add(b.get("name", ""))
        if b.get("tier") and b["tier"] not in VALID_TIERS:
            problems.append(f"{label}: invalid tier {b['tier']!r}")
        if b.get("target") and b["target"] not in VALID_TARGETS:
            problems.append(f"{label}: invalid target {b['target']!r}")
        if b.get("path") and not (repo_root / b["path"]).is_dir():
            problems.append(f"{label}: path '{b['path']}' does not exist")
    return problems
