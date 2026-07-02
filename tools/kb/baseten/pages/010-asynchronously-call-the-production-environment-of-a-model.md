# Asynchronously call the production environment of a model.
Source: https://docs.baseten.co/api-reference/non-regional/asynchronously-call-the-production-environment-of-a-model

/reference/inference-api/inference-api-spec.json post /production/async_predict
Enqueues an asynchronous predict request for the deployment promoted to the production environment. Returns a request ID that can be used to poll for status or cancel the request.
