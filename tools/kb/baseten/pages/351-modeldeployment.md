# ModelDeployment
Source: https://docs.baseten.co/reference/sdk/truss/model-deployment

The object returned by truss.push().

### *class* `truss.api.definitions.ModelDeployment`

Represents a deployed model (returned by `truss.push()`).

**Attributes**

`model_id` → `str`: Unique ID of the deployed model.
`model_deployment_id` → `str`: Unique ID of the model deployment.

**Methods**

`wait_for_active(timeout_seconds: int = 600)` → bool
Waits for the deployment to become **active**.

| Name              | Type  | Description                                         |
| ----------------- | ----- | --------------------------------------------------- |
| `timeout_seconds` | *int* | Maximum time to wait in seconds. Defaults to `600`. |

**Returns**: `true` when deployment is ready.
**Raises**: `TimeoutError` if the deployment doesn't become active within `timeout_seconds`. `ValueError` if deployment fails.
