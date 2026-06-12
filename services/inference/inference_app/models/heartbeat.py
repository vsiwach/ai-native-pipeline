from pydantic import BaseModel


class HealthResult(BaseModel):
    """Shape of GET /healthz — see contracts/inference.openapi.yaml."""

    status: str
