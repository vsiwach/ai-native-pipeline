# Call the production environment of a model.
Source: https://docs.baseten.co/api-reference/non-regional/call-the-production-environment-of-a-model

/reference/inference-api/inference-api-spec.json post /production/predict
Sends a synchronous predict request to the deployment promoted to the production environment. The request body is forwarded directly to the model's `predict` function.
