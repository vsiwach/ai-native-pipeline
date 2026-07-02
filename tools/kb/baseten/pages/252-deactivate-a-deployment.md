# Deactivate a deployment
Source: https://docs.baseten.co/reference/loops-api/deployments/deactivate-a-deployment

post /v1/loops/deployments/{deployment_id}/deactivate
Shut down a Loops deployment by ID. Saved checkpoints remain accessible. Resolving base_model -> deployment_id is the caller's responsibility — list deployments and pick the active one.
