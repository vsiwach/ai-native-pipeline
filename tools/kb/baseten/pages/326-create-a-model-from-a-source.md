# Create a model from a source
Source: https://docs.baseten.co/reference/management-api/models/creates-a-model-from-a-source

post /v1/models
Creates a new model in the caller's organization. The `source` field selects how the model is constructed (currently: `library_listing` — fork an accessible listing from `GET /v1/library_models`). The deployment isn't instantly ready — poll GET endpoint until status is ACTIVE.
