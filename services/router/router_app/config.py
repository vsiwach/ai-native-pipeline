"""Config loading for the router: inference-registry.yaml + routing-policy.yaml.

Both files live at the repo root in development and are copied to the image
root in Docker; override locations with REGISTRY_PATH / ROUTING_POLICY_PATH.
"""

import os
from pathlib import Path

import yaml

def _default_root() -> Path:
    """Repo root in development; the package's grandparent (/srv) in the
    container, where the Dockerfile copies both YAML files."""
    here = Path(__file__).resolve()
    return here.parents[3] if len(here.parents) > 3 else here.parents[1]


def registry_path() -> Path:
    return Path(os.environ.get(
        "REGISTRY_PATH", _default_root() / "inference-registry.yaml"))


def policy_path() -> Path:
    return Path(os.environ.get(
        "ROUTING_POLICY_PATH", _default_root() / "routing-policy.yaml"))


def load_registry(path: Path | None = None) -> dict:
    """Returns {model_name: {tier, target, ...}} from the backends section."""
    data = yaml.safe_load((path or registry_path()).read_text()) or {}
    return data.get("backends") or {}


def load_policy(path: Path | None = None) -> dict:
    data = yaml.safe_load((path or policy_path()).read_text()) or {}
    data.setdefault("tiers", {})
    data.setdefault("cost_table", {})
    data.setdefault("cache", {"enabled": False})
    data.setdefault("endpoints", {})
    return data
