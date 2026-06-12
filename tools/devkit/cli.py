#!/usr/bin/env python3
"""./dev — single entry point for the ai-native-pipeline repo.

Commands:
  status                      where the repo is in the phase plan + next step
  doctor                      check toolchain and repo health
  build                       bazel build //... (when a workspace exists)
  test                        bazel test //... or plain-unittest fallback
  check [--action X]          registry + artifacts + policy + tests (pre-push)
  new service <name>          scaffold a contract-compliant service
      [--tier realtime|standard|batch] [--target cpu|gpu]
  run <service> [--port N]    docker build + run + /healthz probe
"""

import argparse
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import checks
import doctor
import scaffold
import status
import ui

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def cmd_build(args) -> int:
    if not shutil.which("bazel"):
        ui.fail("bazel not installed — see https://bazel.build/install")
        return 1
    if not ((REPO_ROOT / "WORKSPACE").exists() or (REPO_ROOT / "MODULE.bazel").exists()):
        ui.warn("no WORKSPACE/MODULE.bazel yet — run Phase 1 first (./dev status)")
        return 1
    return subprocess.run(["bazel", "build", "//..."], cwd=REPO_ROOT).returncode


def cmd_test(args) -> int:
    return 1 if checks.run_tests(REPO_ROOT) else 0


def cmd_new_service(args) -> int:
    try:
        created = scaffold.create_service(REPO_ROOT, args.name, args.tier, args.target)
    except ValueError as exc:
        ui.fail(str(exc))
        return 1
    ui.heading(f"Created service '{args.name}' ({args.tier}/{args.target})")
    for path in created:
        ui.ok(str(path.relative_to(REPO_ROOT)))
    ui.ok("inference-registry.yaml entry added")
    print()
    print("Next steps:")
    print(f"  1. Put real inference in services/{args.name}/app.py (predict())")
    print(f"  2. ./dev test")
    print(f"  3. ./dev run {args.name}")
    print(f"  4. Add a row to the README architecture table, then ./dev check")
    return 0


def cmd_run(args) -> int:
    if not shutil.which("docker"):
        ui.fail("docker not installed")
        return 1
    name, port = args.name, args.port
    dockerfile = REPO_ROOT / "services" / name / "Dockerfile"
    if not dockerfile.exists():
        ui.fail(f"services/{name}/Dockerfile not found")
        return 1

    tag = f"{name}:dev"
    ui.heading(f"Building {tag}")
    if subprocess.run(
        ["docker", "build", "-f", str(dockerfile), "-t", tag, "."], cwd=REPO_ROOT
    ).returncode != 0:
        return 1

    container = f"{name}-dev"
    subprocess.run(["docker", "rm", "-f", container], capture_output=True)
    if subprocess.run(
        ["docker", "run", "-d", "--rm", "-p", f"{port}:8080",
         "--name", container, tag], cwd=REPO_ROOT,
    ).returncode != 0:
        return 1

    ui.heading("Probing /healthz")
    for _ in range(20):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2):
                ui.ok(f"{name} is healthy at http://127.0.0.1:{port}")
                print(f"\n  try:  curl -s http://127.0.0.1:{port}/v1/info")
                print(f"  stop: docker rm -f {container}")
                return 0
        except (urllib.error.URLError, OSError):
            time.sleep(1)
    ui.fail("service never became healthy; logs:")
    subprocess.run(["docker", "logs", container])
    subprocess.run(["docker", "rm", "-f", container], capture_output=True)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dev", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="phase progress and next step")
    sub.add_parser("doctor", help="check toolchain and repo health")
    sub.add_parser("build", help="bazel build //...")
    sub.add_parser("test", help="run all tests (bazel or unittest fallback)")

    p_check = sub.add_parser("check", help="all pre-push checks")
    p_check.add_argument("--action", default="push",
                         help="governance action to validate (default: push)")

    p_new = sub.add_parser("new", help="scaffold things")
    new_sub = p_new.add_subparsers(dest="kind", required=True)
    p_svc = new_sub.add_parser("service", help="scaffold an inference service")
    p_svc.add_argument("name", help="service name (lowercase, hyphens ok)")
    p_svc.add_argument("--tier", default="standard",
                       choices=["realtime", "standard", "batch"])
    p_svc.add_argument("--target", default="cpu", choices=["cpu", "gpu"])

    p_run = sub.add_parser("run", help="docker build+run a service, probe healthz")
    p_run.add_argument("name")
    p_run.add_argument("--port", type=int, default=8080)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    dispatch = {
        "status": lambda: status.run(REPO_ROOT),
        "doctor": lambda: doctor.run(REPO_ROOT),
        "build": lambda: cmd_build(args),
        "test": lambda: cmd_test(args),
        "check": lambda: checks.run(REPO_ROOT, args.action),
        "new": lambda: cmd_new_service(args),
        "run": lambda: cmd_run(args),
    }
    return dispatch[args.command]()


if __name__ == "__main__":
    sys.exit(main())
