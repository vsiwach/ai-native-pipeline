"""`./dev doctor` — check the toolchain and repo health in one pass."""

import shutil
import subprocess
import sys
from pathlib import Path

import registry
import ui


def _version(cmd: list[str]) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return (out.stdout or out.stderr).strip().splitlines()[0]
    except Exception:
        return ""


def run(repo_root: Path) -> int:
    failures = 0

    ui.heading("Toolchain")
    if sys.version_info >= (3, 11):
        ui.ok(f"python {sys.version.split()[0]}")
    else:
        ui.fail(f"python {sys.version.split()[0]} — repo requires 3.11+")
        failures += 1

    for tool, required_by in (
        ("bazel", "build/test (`./dev build`, `./dev test`)"),
        ("docker", "containers (`./dev run`)"),
        ("git", "version control"),
    ):
        if shutil.which(tool):
            ui.ok(f"{tool} — {ui.dim(_version([tool, '--version']))}")
        else:
            ui.warn(f"{tool} not found — needed for {required_by}")

    ui.heading("Repo layout")
    expected = {
        "CLAUDE.md": "agent instructions",
        "contracts/inference.openapi.yaml": "inference contract (Phase 1)",
        "services/router": "router service (Phase 3)",
        "governance/agent-policy.yaml": "agent governance",
        "inference-registry.yaml": "backend registry",
        "WORKSPACE": "bazel workspace",
    }
    for rel, what in expected.items():
        path = repo_root / rel
        if path.exists():
            ui.ok(rel)
        else:
            ui.info(f"{rel} missing — {what} (fine if that phase hasn't run yet)")

    problems = registry.validate(repo_root)
    if problems:
        ui.heading("Registry problems")
        for p in problems:
            ui.fail(p)
        failures += len(problems)

    print()
    if failures:
        print(ui.red(f"{failures} problem(s) found."))
        return 1
    print(ui.green("Environment looks good."))
    return 0
