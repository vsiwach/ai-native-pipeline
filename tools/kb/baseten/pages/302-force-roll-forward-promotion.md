# Force roll forward promotion
Source: https://docs.baseten.co/reference/management-api/deployments/promote/force-roll-forward-promotion

post /v1/models/{model_id}/environments/{env_name}/force_roll_forward_promotion
Immediately completes the rolling promotion, shifting all traffic to the new version. This works even if the promotion is in the process of rolling back.

Force roll forward takes effect between promotion steps, not immediately. Traffic shifts fully to the candidate deployment at the next step boundary. See [Deployment control actions](/deployment/rolling-deployments#deployment-control-actions) for details.
