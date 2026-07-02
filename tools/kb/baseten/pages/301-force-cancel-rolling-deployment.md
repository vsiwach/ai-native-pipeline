# Force cancel rolling deployment
Source: https://docs.baseten.co/reference/management-api/deployments/promote/force-cancel-promotion

post /v1/models/{model_id}/environments/{env_name}/force_cancel_promotion
Immediately cancels an in-progress rolling promotion and triggers rollback to the previous version.
