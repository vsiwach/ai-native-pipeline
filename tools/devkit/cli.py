#!/usr/bin/env python3
"""./dev — single entry point for the ai-native-pipeline repo.

Commands:
  status                      where the repo is in the phase plan + next step
  doctor                      check toolchain and repo health
  build                       bazel build //... (when a workspace exists)
  test                        bazel test //... or plain-unittest fallback
  check [--action X]          registry + artifacts + policy + tests (pre-push)
  sync [--check]              regenerate inference-registry.yaml from service.py
      [--dockerfiles]         (or --check it in CI; --dockerfiles to preview)
  new service <name>          scaffold a contract-compliant service
      [--tier realtime|standard|batch] [--target cpu|gpu]
  run <service> [--port N]    docker build + run + /healthz probe
  bench <args...>             $/Mtok at fixed SLO (tools/bench.py)
  certify <args...>           signed parity certs (tools/certify.py);
                              a passing run updates vercel-deploy/certs/latest.json
"""

import argparse
import json
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
import sync
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


def _chat(port: int, prompt: str, model: str, stream: bool) -> int:
    """POST a chat completion to a running LLM service (stdlib only)."""
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    payload = json.dumps({
        "model": model, "stream": stream, "max_tokens": 48,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(url, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            cache = resp.headers.get("X-Cache", "?")
            ttft = resp.headers.get("X-TTFT-Ms", "?")
            if stream:
                ui.heading(f"streaming (cache={cache}, ttft={ttft}ms)")
                for raw in resp:
                    line = raw.decode().strip()
                    if not line.startswith("data:") or line == "data: [DONE]":
                        continue
                    delta = json.loads(line[5:]).get("choices", [{}])[0]
                    sys.stdout.write(delta.get("delta", {}).get("content", ""))
                    sys.stdout.flush()
                print()
            else:
                body = json.loads(resp.read())
                print(body["choices"][0]["message"]["content"])
                ui.info(f"cache={cache}  ttft={ttft}ms  "
                        f"tokens={body['usage']['completion_tokens']}")
        return 0
    except (urllib.error.URLError, OSError) as exc:
        ui.fail(f"chat failed ({exc}); is the service running? `./dev run {model}`")
        return 1


def cmd_chat(args) -> int:
    return _chat(args.port, args.prompt, args.model, args.stream)


def cmd_scale_demo(args) -> int:
    """Run the deterministic autoscaling simulation (scale-to-zero + burst)."""
    script = REPO_ROOT / "services/router/scripts/autoscale_demo.py"
    return subprocess.run(["python3", str(script)]).returncode


def cmd_release_demo(args) -> int:
    """Run the release-engine simulation (canary, auto-rollback, shadow)."""
    script = REPO_ROOT / "services/router/scripts/release_demo.py"
    return subprocess.run(["python3", str(script)]).returncode


def link_latest_cert(repo_root: Path, out_dir: str = "certs") -> Path | None:
    """Point vercel-deploy/certs/latest.json at the newest cert record so the
    demo console always renders the cert that actually gated promotion.
    Relative symlink; returns the target or None when no cert exists."""
    certs = sorted((repo_root / out_dir).glob("*.cert.json"),
                   key=lambda p: p.stat().st_mtime)
    if not certs:
        return None
    link = repo_root / "vercel-deploy" / "certs" / "latest.json"
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(Path("../..") / certs[-1].relative_to(repo_root))
    return certs[-1]


def _tool_passthrough(tool: str, extra: list[str]) -> int:
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "tools" / tool), *extra],
        cwd=REPO_ROOT).returncode


def cmd_bench(args) -> int:
    """$/Mtok at fixed SLO — thin wrapper over tools/bench.py."""
    return _tool_passthrough("bench.py", args.args)


def cmd_certify(args) -> int:
    """Signed parity certs — wrapper over tools/certify.py. On a successful
    `run` (verdict PROMOTE_ELIGIBLE) the newest cert becomes
    vercel-deploy/certs/latest.json."""
    rc = _tool_passthrough("certify.py", args.args)
    if rc == 0 and args.args[:1] == ["run"]:
        out_dir = "certs"
        if "--out" in args.args:
            out_dir = args.args[args.args.index("--out") + 1]
        target = link_latest_cert(REPO_ROOT, out_dir)
        if target is not None:
            ui.ok(f"vercel-deploy/certs/latest.json -> "
                  f"{target.relative_to(REPO_ROOT)}")
    return rc


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

    def _capabilities(port: int) -> list:
        try:
            with urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/v1/info", timeout=2) as resp:
                return json.loads(resp.read()).get("capabilities", [])
        except (urllib.error.URLError, OSError, ValueError):
            return []

    for _ in range(20):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2):
                ui.ok(f"{name} is healthy at http://127.0.0.1:{port}")
                # chat-capable backend? boot a sample chat (Phase 6 acceptance).
                caps = _capabilities(port)
                if "chat" in caps:
                    ui.heading("sample chat")
                    _chat(port, "In one sentence, what is prefill vs decode?",
                          name, stream=True)
                    print(f"\n  more: ./dev chat \"your prompt\" --port {port}")
                else:
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

    p_sync = sub.add_parser("sync", help="regenerate registry from service.py manifests")
    p_sync.add_argument("--check", action="store_true",
                        help="fail if the registry is out of date (CI mode)")
    p_sync.add_argument("--dockerfiles", action="store_true",
                        help="print each manifest's rendered Dockerfile and exit")

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

    p_chat = sub.add_parser("chat", help="send a chat completion to a running LLM service")
    p_chat.add_argument("prompt")
    p_chat.add_argument("--port", type=int, default=8080)
    p_chat.add_argument("--model", default="llm-sim")
    p_chat.add_argument("--stream", action="store_true")

    sub.add_parser("scale-demo",
                   help="simulate cold-start-aware autoscaling (scale-to-zero + burst)")
    sub.add_parser("release-demo",
                   help="simulate the release engine (canary, auto-rollback, shadow)")

    p_bench = sub.add_parser(
        "bench", help="measure $/Mtok at fixed SLO (tools/bench.py passthrough)")
    p_bench.add_argument("args", nargs=argparse.REMAINDER,
                         help="forwarded to tools/bench.py (see --help there)")
    p_certify = sub.add_parser(
        "certify", help="signed parity certs (tools/certify.py passthrough; "
        "a passing run updates vercel-deploy/certs/latest.json)")
    p_certify.add_argument("args", nargs=argparse.REMAINDER,
                           help="forwarded to tools/certify.py")

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
        "sync": lambda: (sync.print_dockerfiles(REPO_ROOT) if args.dockerfiles
                         else sync.sync(REPO_ROOT, check=args.check)),
        "new": lambda: cmd_new_service(args),
        "run": lambda: cmd_run(args),
        "chat": lambda: cmd_chat(args),
        "scale-demo": lambda: cmd_scale_demo(args),
        "release-demo": lambda: cmd_release_demo(args),
        "bench": lambda: cmd_bench(args),
        "certify": lambda: cmd_certify(args),
    }
    return dispatch[args.command]()


if __name__ == "__main__":
    sys.exit(main())
