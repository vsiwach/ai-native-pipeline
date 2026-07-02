# Development model deployment
Source: https://docs.baseten.co/reference/management-api/deployments/autoscaling/updates-a-development-deployments-autoscaling-settings

patch /v1/models/{model_id}/deployments/development/autoscaling_settings
Updates a development deployment's autoscaling settings and returns the update status.

<Note>
  To update autoscaling settings at the environment level, use the [update environment settings](/reference/management-api/environments/update-an-environments-settings) endpoint.
</Note>
