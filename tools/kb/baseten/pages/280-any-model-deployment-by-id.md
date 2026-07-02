# Any model deployment by ID
Source: https://docs.baseten.co/reference/management-api/deployments/autoscaling/updates-a-deployments-autoscaling-settings

patch /v1/models/{model_id}/deployments/{deployment_id}/autoscaling_settings
Updates a deployment's autoscaling settings and returns the update status.

<Note>
  To update autoscaling settings at the environment level, use the [update environment settings](/reference/management-api/environments/update-an-environments-settings) endpoint.
</Note>
