"""`./dev check` — the one command to run before pushing.

Aggregates: registry validation, governance policy check (when present),
per-service artifact completeness, and the test suite.
"""

import shutil
import subprocess
from pathlib import Path

import registry
import ui

REQUIRED_SERVICE_FILES = ("Dockerfile", "BUILD.bazel", "README.md")


def check_registry(repo_root: Path) -> int:
    problems = registry.validate(repo_root)
    if not registry.registry_path(repo_root).exists():
        ui.info("inference-registry.yaml not created yet — skipping")
        return 0
    for p in problems:
        ui.fail(p)
    if not problems:
        ui.ok(f"registry valid ({len(registry.load(repo_root))} backend(s))")
    return len(problems)


def check_service_artifacts(repo_root: Path) -> int:
    """Every service must ship Dockerfile, BUILD.bazel, README, tests/."""
    services_dir = repo_root / "services"
    if not services_dir.is_dir():
        ui.info("no services/ yet — skipping")
        return 0
    failures = 0
    for svc in sorted(p for p in services_dir.iterdir() if p.is_dir()):
        missing = [f for f in REQUIRED_SERVICE_FILES if not (svc / f).exists()]
        if not (svc / "tests").is_dir():
            missing.append("tests/")
        if missing:
            ui.fail(f"services/{svc.name}: missing {', '.join(missing)}")
            failures += 1
        else:
            ui.ok(f"services/{svc.name}: all required artifacts present")
    return failures


def check_policy(repo_root: Path, action: str) -> int:
    policy_tool = repo_root / "tools" / "policy_check.py"
    if not policy_tool.exists():
        ui.info("tools/policy_check.py not present yet — skipping")
        return 0
    result = subprocess.run(
        ["python3", str(policy_tool), "--action", action],
        cwd=repo_root, capture_output=True, text=True,
    )
    if result.returncode == 0:
        ui.ok(f"policy check passed for action '{action}'")
        return 0
    ui.fail(f"policy check failed: {(result.stdout + result.stderr).strip()}")
    return 1


def run_tests(repo_root: Path) -> int:
    """Bazel when available, plain unittest discovery otherwise."""
    if shutil.which("bazel") and (
        (repo_root / "WORKSPACE").exists() or (repo_root / "MODULE.bazel").exists()
    ):
        ui.info("running: bazel test //...")
        return subprocess.run(["bazel", "test", "//..."], cwd=repo_root).returncode

    test_dirs = sorted(
        d for d in repo_root.glob("*/**/tests") if d.is_dir()
        and not any(part.startswith(".") for part in d.parts)
    )
    if not test_dirs:
        ui.info("no tests found yet — skipping")
        return 0
    failures = 0
    for tests in test_dirs:
        rel = tests.relative_to(repo_root)
        result = subprocess.run(
            ["python3", "-m", "unittest", "discover", "-s", str(tests), "-v"],
            cwd=repo_root, capture_output=True, text=True,
        )
        if result.returncode == 0:
            last = result.stderr.strip().splitlines()[-1] if result.stderr else "OK"
            ui.ok(f"{rel} — {last}")
        else:
            ui.fail(f"{rel} failed:\n{result.stderr}")
            failures += 1
    return failures


def run(repo_root: Path, action: str = "push") -> int:
    failures = 0
    ui.heading("Registry")
    failures += check_registry(repo_root)
    ui.heading("Service artifacts")
    failures += check_service_artifacts(repo_root)
    ui.heading("Governance")
    failures += check_policy(repo_root, action)
    ui.heading("Tests")
    failures += run_tests(repo_root)
    print()
    if failures:
        print(ui.red(f"check failed — {failures} problem(s). Fix before pushing."))
        return 1
    print(ui.green("All checks passed. Safe to push."))
    return 0
