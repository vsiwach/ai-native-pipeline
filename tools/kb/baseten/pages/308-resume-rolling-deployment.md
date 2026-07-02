# Resume rolling deployment
Source: https://docs.baseten.co/reference/management-api/deployments/promote/resume-promotion

post /v1/models/{model_id}/environments/{env_name}/resume_promotion
Resumes a paused rolling promotion, continuing from where it was paused.

Resume continues the rolling deployment from where it was paused. The deployment returns to `RAMPING_UP` and proceeds with the remaining promotion steps. See [Deployment control actions](/deployment/rolling-deployments#deployment-control-actions) for details.
