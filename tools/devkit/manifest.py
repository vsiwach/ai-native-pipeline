"""Resources-as-code service manifests — the Modal-style DX layer.

Modal's core ergonomic win is that a service's *environment* (its container
image) and its *runtime resources* (GPU/CPU tier, scaling) live in code, right
next to the service, instead of in a separate YAML/Dockerfile that drifts out of
sync. This module brings that pattern into the repo without depending on Modal's
platform.

You declare a service like this (see services/inference/service.py):

    from manifest import Image, service

    image = (
        Image.debian_slim("3.11")
        .copy("services/inference/requirements.txt", ".")
        .pip_install_requirements("requirements.txt")
        .copy("services/inference/inference_app", "./inference_app")
        .expose(8080)
        .cmd(["uvicorn", "inference_app.main:app", "--host", "0.0.0.0",
              "--port", "8080"])
    )

    SERVICE = service(
        name="house-price-reg",
        path="services/inference",
        tier="standard",          # realtime | standard | batch
        target="cpu",             # cpu | gpu
        max_replicas=3,
        scale_to_zero=True,
        image=image,
    )

`./dev sync` then GENERATES inference-registry.yaml from every service.py, so
the registry the router reads is always a projection of code — never a thing you
hand-edit and forget. `./dev sync --check` fails CI if they've drifted.

Stdlib-only on purpose: `./dev sync` imports these manifests, so they must not
pull in FastAPI/torch/etc. Keep service.py free of heavy imports — declare the
image, don't import the app.
"""

from dataclasses import dataclass, field

VALID_TIERS = ("realtime", "standard", "batch")
VALID_TARGETS = ("cpu", "gpu")
VALID_ENGINES = ("max", "sklearn", "baseten", "vllm", "baseten-api")


class Image:
    """A container image defined by method chaining, Modal-style.

    Every method returns a new Image so chains are pure and reusable. Render to
    a Dockerfile with `.to_dockerfile()`. Each call appends one build step; the
    order you write them is the order they run.
    """

    def __init__(self, steps: tuple[str, ...] = ()):
        self._steps = tuple(steps)

    # --- base images -----------------------------------------------------
    @classmethod
    def from_registry(cls, ref: str) -> "Image":
        """Start from any image reference, e.g. 'python:3.11-slim'."""
        return cls((f"FROM {ref}",))

    @classmethod
    def debian_slim(cls, python_version: str = "3.11") -> "Image":
        """Start from the official slim Python image (Debian-based)."""
        return cls.from_registry(f"python:{python_version}-slim")

    # --- build steps (each returns a new Image) --------------------------
    def _add(self, *lines: str) -> "Image":
        return Image(self._steps + lines)

    def workdir(self, path: str) -> "Image":
        return self._add(f"WORKDIR {path}")

    def copy(self, src: str, dest: str) -> "Image":
        return self._add(f"COPY {src} {dest}")

    def run(self, command: str) -> "Image":
        return self._add(f"RUN {command}")

    def apt_install(self, *packages: str) -> "Image":
        pkgs = " ".join(packages)
        return self._add(
            "RUN apt-get update && apt-get install -y --no-install-recommends "
            f"{pkgs} && rm -rf /var/lib/apt/lists/*"
        )

    def pip_install(self, *packages: str) -> "Image":
        return self._add(f"RUN pip install --no-cache-dir {' '.join(packages)}")

    def pip_install_requirements(self, requirements_path: str) -> "Image":
        return self._add(
            f"RUN pip install --no-cache-dir -r {requirements_path}"
        )

    def env(self, **values: str) -> "Image":
        return self._add(*(f"ENV {k}={v}" for k, v in values.items()))

    def user(self, name: str) -> "Image":
        return self._add(f"USER {name}")

    def expose(self, port: int) -> "Image":
        return self._add(f"EXPOSE {port}")

    def healthcheck(self, command: str, *, interval: str = "10s",
                    timeout: str = "3s", start_period: str | None = None) -> "Image":
        opts = f"--interval={interval} --timeout={timeout}"
        if start_period:
            opts += f" --start-period={start_period}"
        return self._add(f"HEALTHCHECK {opts} CMD {command}")

    def cmd(self, argv: list[str]) -> "Image":
        rendered = ", ".join(f'"{a}"' for a in argv)
        return self._add(f"CMD [{rendered}]")

    # --- output ----------------------------------------------------------
    def to_dockerfile(self) -> str:
        """Render these steps as a Dockerfile."""
        if not self._steps or not self._steps[0].startswith("FROM"):
            raise ValueError("image must start from a base (e.g. Image.debian_slim())")
        return "\n".join(self._steps) + "\n"


@dataclass(frozen=True)
class Service:
    """A deployable inference backend, declared as code.

    Maps 1:1 to an inference-registry.yaml entry. `./dev sync` reads these and
    writes the registry the router consumes.
    """

    name: str
    path: str
    tier: str
    target: str
    max_replicas: int = 3
    scale_to_zero: bool = True
    image: Image | None = field(default=None, repr=False)
    # 'backends' = routing target behind the router; 'services' =
    # infrastructure (e.g. the router itself) — CI-built, never routed to.
    section: str = "backends"
    # --- LLM serving fields (Phase 6+). Optional: only emitted to the registry
    # when set, so non-LLM entries stay byte-identical. engine selects the
    # BackendAdapter; cold_start_s / kv_ttl_s parameterize the simulator's
    # economics; model_id is the HF id a real `max serve` would load.
    engine: str | None = None        # max | sklearn
    cold_start_s: float | None = None
    kv_ttl_s: float | None = None
    model_id: str | None = None

    def __post_init__(self) -> None:
        if self.tier not in VALID_TIERS:
            raise ValueError(f"tier must be one of {VALID_TIERS}, got {self.tier!r}")
        if self.target not in VALID_TARGETS:
            raise ValueError(
                f"target must be one of {VALID_TARGETS}, got {self.target!r}"
            )
        if self.section not in ("backends", "services"):
            raise ValueError(
                f"section must be 'backends' or 'services', got {self.section!r}"
            )
        if self.engine is not None and self.engine not in VALID_ENGINES:
            raise ValueError(
                f"engine must be one of {VALID_ENGINES}, got {self.engine!r}"
            )

    def to_registry_entry(self) -> str:
        """Render this service as its inference-registry.yaml block.

        Byte-compatible with what `registry.add` writes, so generating the
        registry from manifests reproduces a hand-written one exactly. Optional
        LLM fields are appended only when set.
        """
        lines = [
            f"  {self.name}:\n",
            f"    path: {self.path}\n",
            f"    tier: {self.tier}\n",
            f"    target: {self.target}\n",
            f"    max_replicas: {self.max_replicas}\n",
            f"    scale_to_zero: {'true' if self.scale_to_zero else 'false'}\n",
        ]
        if self.engine is not None:
            lines.append(f"    engine: {self.engine}\n")
        if self.model_id is not None:
            lines.append(f"    model_id: {self.model_id}\n")
        if self.cold_start_s is not None:
            lines.append(f"    cold_start_s: {self.cold_start_s}\n")
        if self.kv_ttl_s is not None:
            lines.append(f"    kv_ttl_s: {self.kv_ttl_s}\n")
        return "".join(lines)


def service(name: str, path: str, tier: str, target: str,
            max_replicas: int = 3, scale_to_zero: bool = True,
            image: Image | None = None, section: str = "backends",
            engine: str | None = None, cold_start_s: float | None = None,
            kv_ttl_s: float | None = None, model_id: str | None = None) -> Service:
    """Declare a service. Thin wrapper over Service for a Modal-like call site."""
    return Service(
        name=name, path=path, tier=tier, target=target,
        max_replicas=max_replicas, scale_to_zero=scale_to_zero, image=image,
        section=section, engine=engine, cold_start_s=cold_start_s,
        kv_ttl_s=kv_ttl_s, model_id=model_id,
    )
