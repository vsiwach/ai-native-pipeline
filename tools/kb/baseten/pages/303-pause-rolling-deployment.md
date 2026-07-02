# Pause rolling deployment
Source: https://docs.baseten.co/reference/management-api/deployments/promote/pause-promotion

post /v1/models/{model_id}/environments/{env_name}/pause_promotion
Pauses an in-progress rolling promotion after the current step completes. No further scaling changes are made until resumed.

Pause takes effect between promotion steps, not immediately. Replica changes already in progress finish before the rolling deployment settles into `PAUSED`. See [Deployment control actions](/deployment/rolling-deployments#deployment-control-actions) for details.
