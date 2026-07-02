# Get model deployment config
Source: https://docs.baseten.co/reference/management-api/deployments/get-deployment-config

get /v1/models/{model_id}/deployments/{deployment_id}/config
Returns the deployment's config. `output_format` query param picks the shape: 'raw' (config.yaml text), 'parsed' (dict with defaults), or 'both' (default).
