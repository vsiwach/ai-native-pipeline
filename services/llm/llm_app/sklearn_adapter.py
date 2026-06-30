"""SklearnPredict — wraps the legacy /v1/predict backend in the same
BackendAdapter interface, proving the interface is uniform across LLM and
non-LLM backends. It advertises {"predict"}, not {"chat"}.

It proxies to the existing services/inference service over HTTP (the contract
boundary), so this adapter carries no model code and stays cloud-neutral.
"""

from llm_app.adapter import BackendAdapter


class SklearnPredict(BackendAdapter):
    engine = "sklearn"
    target = "cpu"

    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url.rstrip("/")

    def capabilities(self) -> set[str]:
        return {"predict"}

    def info(self) -> dict:
        base = super().info()
        base.update({"backend": "sklearn-predict", "base_url": self.base_url})
        return base

    def predict(self, payload: dict) -> dict:
        import httpx
        resp = httpx.post(f"{self.base_url}/v1/predict", json=payload,
                          timeout=30)
        resp.raise_for_status()
        return resp.json()

    def healthz(self) -> dict:
        try:
            import httpx
            r = httpx.get(f"{self.base_url}/healthz", timeout=5)
            return {"status": "ok" if r.status_code == 200 else "down"}
        except Exception:  # noqa: BLE001
            return {"status": "down"}
