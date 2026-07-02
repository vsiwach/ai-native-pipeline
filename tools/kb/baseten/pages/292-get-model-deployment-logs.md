# Get model deployment logs
Source: https://docs.baseten.co/reference/management-api/deployments/get-deployment-logs

get /v1/models/{model_id}/deployments/{deployment_id}/logs
Gets all the logs for a model deployment in the given time range, which defaults to the last 30 minutes. A failed or older deployment may only have logs from before that window; pass `start_epoch_millis` to widen it back to the build/deploy time.

<Note>
  This endpoint is in beta. The request and response structure may change before it's generally available.
</Note>
