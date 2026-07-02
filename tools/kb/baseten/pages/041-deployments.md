# Deployments
Source: https://docs.baseten.co/deployment/deployments

Deploy, manage, and scale machine learning models with Baseten

A *deployment* in Baseten is a containerized instance of a model that serves inference requests through an API endpoint. Deployments exist independently but can be promoted to an environment for structured access and scaling.

Baseten automatically wraps every deployment in a REST API. Once deployed, models can be queried with an HTTP request:

```python predict.py theme={"system"}
import requests

resp = requests.post(
    "https://model-{modelID}.api.baseten.co/deployment/[{deploymentID}]/predict",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={'text': 'Hello my name is {MASK}'},
)

print(resp.json())
```

For the full request and response format, see [running inference on your deployment](/inference/calling-your-model).

## Development deployment

A *development deployment* is a mutable instance designed for rapid iteration. Create one with `truss push --watch` (for models) or `truss chains push --watch` (for Chains). It is always in the development state and cannot be renamed or detached from it.

Key characteristics:

* Live reload enables direct updates without redeployment.
* Single replica, scales to zero when idle to conserve compute resources.
* No autoscaling or zero-downtime updates.
* Can be promoted to create a persistent deployment.

Once promoted, the development deployment transitions to a deployment and can optionally be promoted to an environment.

## Environments and promotion

Environments provide logical isolation for managing deployments but aren't required for a deployment to function. You can run a deployment independently or promote it to an environment for controlled traffic allocation and scaling.

* The production environment exists by default.
* Custom environments (for example, staging) can be created for specific workflows.
* Promoting a deployment doesn't modify its behavior, only its routing and lifecycle management.

### Rolling deployments

Rolling deployments replace replicas incrementally when promoting a deployment to an environment. Instead of swapping all traffic at once, rolling deployments scale up the candidate, shift traffic proportionally, and scale down the previous deployment in controlled steps. You can pause, resume, cancel, or force-complete a rolling deployment at any point.

See [Rolling deployments](/deployment/rolling-deployments) for configuration, control actions, and status reference.

### Canary deployments (deprecated)

<Warning>
  Canary deployments are deprecated. Use [rolling deployments](/deployment/rolling-deployments) for incremental traffic shifting with finer control over replica provisioning and rollback.
</Warning>

Canary deployments support incremental traffic shifting to a new deployment in 10 evenly distributed stages over a configurable time window. Enable or cancel canary rollouts from the UI or [REST API](/reference/management-api/environments/update-an-environments-settings).

## Manage deployments

### Name deployments

By default, deployments of a model are named `deployment-1`, `deployment-2`, and so forth sequentially. You can instead give deployments custom names in two ways:

1. While creating the deployment, using a [command line argument in truss push](/reference/sdk/truss#deploying-a-model).
2. After creating the deployment, in the model management page within your Baseten dashboard.

Renaming deployments is purely aesthetic and doesn't affect model management API paths, which work by model and deployment IDs.

### Label deployments

Labels are JSON key-value metadata you attach to a deployment to organize and track it, for example by team, environment, or the pipeline that created it. Set them at deploy time with the `--labels` flag on `truss push` (`truss push --labels '{"team": "ml-platform", "env": "staging"}'`), the `labels` argument to [`truss.push()`](/reference/sdk/truss/push), or the `labels` input on the [deploy GitHub Action](/reference/ci/github-action). To attach labels automatically in a CI pipeline, see [Deploy with labels](/deployment/ci-cd#deploy-with-labels).

### Deactivate a deployment

Deactivate a deployment to suspend inference execution while preserving configuration.

* Remains visible in the dashboard.
* Consumes no compute resources but can be reactivated anytime.
* API requests return a 404 error while deactivated.

For demand-driven deployments, consider [autoscaling with scale to zero](/reference/management-api/deployments/autoscaling/updates-a-deployments-autoscaling-settings).

### Delete deployments

You can permanently delete deployments, but production deployments must be replaced before deletion.

* Deleted deployments are purged from the dashboard but retained in usage logs.
* All associated compute resources are released.
* API requests return a 404 error post-deletion.

<Warning>
  Deletion is irreversible. Use deactivation if retention is required.
</Warning>
