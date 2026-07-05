"""Manifest for docs-assist (stdlib-only, per repo convention: ./dev sync reads this)."""
try:
    from tools.devkit.manifest import Image, service  # type: ignore
except ImportError:  # manifest layer must import without the devkit on path
    def service(**kw):
        def deco(f):
            f.manifest = kw
            return f
        return deco

    class Image:
        @staticmethod
        def debian_slim():
            return Image()

        def pip_install(self, *pkgs):
            return self


@service(
    name="docs-assist",
    tier="realtime",
    target="cpu",            # the agent shim is CPU; GPUs live behind UPSTREAM_BASE_URL
    max_replicas=3,
    scale_to_zero=True,
    engine="openai-proxy",
    route="docs-assist",
    egress_class="in-vpc",   # context-firewall seed: KB + retrieval never leave
)
def docs_assist():
    return Image.debian_slim().pip_install("fastapi", "uvicorn", "httpx")
