from pydantic import BaseModel


class InfoResult(BaseModel):
    """Shape of GET /v1/info — see contracts/inference.openapi.yaml."""

    model: str
    version: str
    tier: str
    target: str
