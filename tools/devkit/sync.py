"""`./dev sync` — generate inference-registry.yaml from service.py manifests.

This closes the drift gap Modal avoids by design: each service declares its
resources and image as code (services/<name>/service.py), and the registry the
router reads is a generated projection of those declarations.

    ./dev sync                 regenerate inference-registry.yaml from manifests
    ./dev sync --check         exit 1 if the registry is out of date (for CI)
    ./dev sync --dockerfiles   print the Dockerfile each manifest's image renders

A service is discovered if services/<name>/service.py defines a module-level
`SERVICE` (a manifest.Service). Services without a manifest are skipped, so this
can be adopted one service at a time.
"""

import importlib.util
import sys
from pathlib import Path

DEVKIT = Path(__file__).resolve().parent
sys.path.insert(0, str(DEVKIT))

import registry  # noqa: E402  (reuse the header + path helpers)
import ui  # noqa: E402
from manifest import Service  # noqa: E402


def discover(repo_root: Path) -> list[Service]:
    """Import every services/<name>/service.py and collect its SERVICE."""
    services_dir = repo_root / "services"
    found: list[Service] = []
    if not services_dir.is_dir():
        return found
    for service_py in sorted(services_dir.glob("*/service.py")):
        mod_name = f"_manifest_{service_py.parent.name.replace('-', '_')}"
        spec = importlib.util.spec_from_file_location(mod_name, service_py)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        svc = getattr(module, "SERVICE", None)
        if isinstance(svc, Service):
            found.append(svc)
        else:
            ui.warn(f"{service_py.relative_to(repo_root)}: no SERVICE defined — skipped")
    return found


def render_registry(services: list[Service], current: str = "") -> str:
    """Render inference-registry.yaml, regenerating only the `backends:` block.

    Non-destructive: the file's existing header and any sections after the
    backends block (e.g. an infra `services:` section the router build owns) are
    preserved verbatim. Only the backend entries are projected from manifests,
    so this can never clobber hand- or tool-managed content elsewhere.
    Manifests with section="services" (infrastructure like the router) are
    never projected here — their entries live in that preserved tail.
    """
    entries = "".join(
        s.to_registry_entry()
        for s in sorted(services, key=lambda s: s.name)
        if s.section == "backends"
    )
    entry_lines = entries.splitlines()

    if not current.strip():
        return registry.REGISTRY_HEADER + entries

    lines = current.splitlines()
    bi = next(
        (i for i, ln in enumerate(lines)
         if ln.strip() == "backends:" and not ln.startswith(" ")),
        None,
    )
    if bi is None:
        # No backends section yet — prepend one, keep the rest untouched.
        return "backends:\n" + entries + "\n" + current

    # Walk past the current backend entries to find where the next section begins.
    last_entry = bi
    k = bi + 1
    while k < len(lines):
        stripped = lines[k].strip()
        if stripped == "":
            k += 1
            continue
        if not lines[k].startswith(" "):  # top-level comment or new section
            break
        last_entry = k
        k += 1

    header = lines[: bi + 1]
    tail = lines[last_entry + 1:]
    return "\n".join(header + entry_lines + tail) + "\n"


def sync(repo_root: Path, check: bool = False) -> int:
    services = discover(repo_root)
    if not services:
        ui.info("no service.py manifests found — nothing to sync")
        return 0

    path = registry.registry_path(repo_root)
    current = path.read_text() if path.exists() else ""
    generated = render_registry(services, current)

    if check:
        if current == generated:
            ui.ok(f"registry up to date with {len(services)} manifest(s)")
            return 0
        ui.fail("inference-registry.yaml is out of date with service.py manifests.")
        ui.info("run `./dev sync` to regenerate it.")
        _print_diff(current, generated)
        return 1

    if current == generated:
        ui.ok(f"registry already in sync ({len(services)} backend(s))")
        return 0
    path.write_text(generated)
    ui.ok(f"wrote {path.name} from {len(services)} manifest(s)")
    return 0


def print_dockerfiles(repo_root: Path) -> int:
    services = discover(repo_root)
    for s in sorted(services, key=lambda s: s.name):
        ui.heading(f"{s.name} → {s.path}/Dockerfile")
        if s.image is None:
            ui.info("no image declared")
            continue
        print(s.image.to_dockerfile())
    return 0


def _print_diff(current: str, generated: str) -> None:
    import difflib
    diff = difflib.unified_diff(
        current.splitlines(), generated.splitlines(),
        fromfile="inference-registry.yaml (on disk)",
        tofile="inference-registry.yaml (from manifests)", lineterm="",
    )
    for line in diff:
        print(line)
