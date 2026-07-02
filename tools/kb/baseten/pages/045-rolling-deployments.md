# Rolling deployments
Source: https://docs.baseten.co/deployment/rolling-deployments

Gradually shift traffic to a new deployment with replica-based rolling deployments.

<RollingDeployEngine />

Rolling deployments replace replicas incrementally when promoting a deployment to an environment.
Instead of swapping all traffic at once, rolling deployments scale up the candidate deployment, shift traffic proportionally, and scale down the previous deployment in controlled steps.
Autoscaling continues throughout the rollout for environments where `min_replica < max_replica`, so both deployments scale up to meet traffic demand as it shifts between them.

Use rolling deployments when you need zero-downtime updates with the ability to pause, cancel, or force-complete the deployment at any point.

<Note>
  Rolling deployments are not supported for [Chains](/chains/overview). This feature is available for individual model deployments only.
</Note>

## How rolling deployments work

A rolling deployment follows a repeating three-step cycle:

1. **Scale up** candidate deployment replicas by the configured percentage.
2. **Shift traffic** proportionally to match the new replica ratio.
3. **Scale down** the previous deployment replicas by the same percentage.

This cycle repeats until all traffic and replicas run on the candidate deployment, at which point it becomes the active deployment in the environment.

The following diagram shows this cycle in action. The tab strip mirrors the promotion lifecycle: a promotion enters `RELEASING` when it starts, sits in `RAMPING_UP` while replicas scale and traffic shifts, can pause as `PAUSED`, and lands at `SUCCEEDED` once the candidate serves all traffic. Click any status to freeze the simulation on that stage, then click it again to resume.

<RollingDeployViz />

<Accordion title="Configure rolling_deploy_config">
  Adjust the values and click **Apply** to restart the simulation with your configuration.

  <RollingDeployConfig />
</Accordion>

### Provisioning modes

Rolling deployments support two mutually exclusive provisioning modes.
You must configure exactly one:

* `max_surge_percent`: Scales up candidate replicas before scaling down previous replicas.
* `max_unavailable_percent`: Scales down previous replicas before scaling up candidate replicas.

Both can't be non-zero at the same time, and both can't be zero at the same time.

## Enable rolling deployments

Enable rolling deployments on any environment by updating the environment's promotion settings.
Rolling deployments are disabled by default.

<Tabs>
  <Tab title="cURL">
    ```bash Request theme={"system"}
    curl -X PATCH \
      https://api.baseten.co/v1/models/{model_id}/environments/production \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
        "promotion_settings": {
          "rolling_deploy": true,
          "rolling_deploy_config": {
            "max_surge_percent": 10,
            "max_unavailable_percent": 0,
            "stabilization_time_seconds": 60,
            "replica_overhead_percent": 0
          }
        }
      }'
    ```
  </Tab>

  <Tab title="Python">
    ```python Request theme={"system"}
    import requests
    import os

    API_KEY = os.environ.get("BASETEN_API_KEY")

    response = requests.patch(
        "https://api.baseten.co/v1/models/{model_id}/environments/production",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "promotion_settings": {
                "rolling_deploy": True,
                "rolling_deploy_config": {
                    "max_surge_percent": 10,
                    "max_unavailable_percent": 0,
                    "stabilization_time_seconds": 60,
                    "replica_overhead_percent": 0,
                },
            }
        },
    )

    print(response.json())
    ```
  </Tab>
</Tabs>

Once rolling deployments are enabled, any subsequent [promotion to the environment](/reference/management-api/deployments/promote/promotes-a-deployment-to-an-environment) uses the rolling deployment workflow.

## Configuration reference

Configure rolling deployments through the `rolling_deploy_config` object in the environment's `promotion_settings`.

<ParamField type="integer">
  Percentage of additional replicas to provision during each step. Set to `0` to use max unavailable mode instead.

  **Range:** 0-50
</ParamField>

<ParamField type="integer">
  Percentage of replicas that can be unavailable during each step. Set to `0` to use max surge mode instead.

  **Range:** 0-50
</ParamField>

<ParamField type="integer">
  Seconds to wait after each traffic shift before proceeding to the next step. Use this to monitor metrics between steps.

  **Range:** 0-3600
</ParamField>

<ParamField type="integer">
  Percentage of additional replicas to pre-provision on the current deployment before the rolling deployment starts. Useful for environments without autoscaling (`min_replica == max_replica`) or as a buffer for anticipated traffic spikes during the rollout.

  **Range:** 0-500
</ParamField>

Additional promotion settings configured at the `promotion_settings` level:

<ParamField type="boolean">
  Enables rolling deployments for the environment.
</ParamField>

## Deployment statuses

The `in_progress_promotion` field on the [environment detail endpoint](/reference/management-api/environments/get-an-environments-details) tracks the current state of a rolling deployment.

| Status         | Description                                                                                                                                        |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RELEASING`    | Candidate deployment is building and initializing replicas.                                                                                        |
| `RAMPING_UP`   | Scaling up candidate replicas and shifting traffic.                                                                                                |
| `PAUSED`       | Rolling deployment is paused at its current traffic split. No further promotion steps run, but in-flight replica changes and autoscaling continue. |
| `RAMPING_DOWN` | Graceful cancel in progress. Traffic is shifting back to the previous deployment.                                                                  |
| `SUCCEEDED`    | Rolling deployment completed. The candidate is now the active deployment.                                                                          |
| `FAILED`       | Rolling deployment failed. Traffic remains on the previous deployment.                                                                             |
| `CANCELED`     | Rolling deployment was canceled. Traffic returned to the previous deployment.                                                                      |

The `in_progress_promotion` object also includes `percent_traffic_to_new_version`, which reports the current percentage of traffic routed to the candidate deployment.

## Deployment control actions

Pause, resume, and force roll forward act on the rolling deployment between steps, not immediately. Replica changes already in progress finish before the action takes effect, so the rolling deployment can keep scaling for a short time after you trigger the action.

For example, if the candidate deployment is at 20% traffic and has just been told to scale from 2 to 4 replicas, clicking pause lets the candidate finish scaling to 4 replicas. The traffic split stays pinned at 20% until you resume.

### Pause

Pauses the rolling deployment. Use this to inspect metrics or logs before proceeding.

<Tabs>
  <Tab title="cURL">
    ```bash Request theme={"system"}
    curl -X POST \
      https://api.baseten.co/v1/models/{model_id}/environments/production/pause_promotion \
      -H "Authorization: Bearer $BASETEN_API_KEY"
    ```
  </Tab>

  <Tab title="Python">
    ```python Request theme={"system"}
    response = requests.post(
        "https://api.baseten.co/v1/models/{model_id}/environments/production/pause_promotion",
        headers={"Authorization": f"Bearer {API_KEY}"},
    )

    print(response.json())
    ```
  </Tab>
</Tabs>

### Resume

Resumes a paused rolling deployment from where it left off.

<Tabs>
  <Tab title="cURL">
    ```bash Request theme={"system"}
    curl -X POST \
      https://api.baseten.co/v1/models/{model_id}/environments/production/resume_promotion \
      -H "Authorization: Bearer $BASETEN_API_KEY"
    ```
  </Tab>

  <Tab title="Python">
    ```python Request theme={"system"}
    response = requests.post(
        "https://api.baseten.co/v1/models/{model_id}/environments/production/resume_promotion",
        headers={"Authorization": f"Bearer {API_KEY}"},
    )

    print(response.json())
    ```
  </Tab>
</Tabs>

### Cancel

Gracefully cancels the rolling deployment. Traffic ramps back to the previous deployment and candidate replicas scale down.

<Tabs>
  <Tab title="cURL">
    ```bash Request theme={"system"}
    curl -X POST \
      https://api.baseten.co/v1/models/{model_id}/environments/production/cancel_promotion \
      -H "Authorization: Bearer $BASETEN_API_KEY"
    ```
  </Tab>

  <Tab title="Python">
    ```python Request theme={"system"}
    response = requests.post(
        "https://api.baseten.co/v1/models/{model_id}/environments/production/cancel_promotion",
        headers={"Authorization": f"Bearer {API_KEY}"},
    )

    print(response.json())
    ```
  </Tab>
</Tabs>

Returns a `status` of `CANCELED` (instant cancel for non-rolling deployments) or `RAMPING_DOWN` (graceful rollback for rolling deployments).

### Force cancel

Immediately cancels the rolling deployment and returns all traffic to the previous deployment. Use this when you need to roll back without waiting for the graceful ramp-down.

<Warning>
  Force canceling may cause brief service disruption if the previous deployment
  is under-provisioned.
</Warning>

<Tabs>
  <Tab title="cURL">
    ```bash Request theme={"system"}
    curl -X POST \
      https://api.baseten.co/v1/models/{model_id}/environments/production/force_cancel_promotion \
      -H "Authorization: Bearer $BASETEN_API_KEY"
    ```
  </Tab>

  <Tab title="Python">
    ```python Request theme={"system"}
    response = requests.post(
        "https://api.baseten.co/v1/models/{model_id}/environments/production/force_cancel_promotion",
        headers={"Authorization": f"Bearer {API_KEY}"},
    )

    print(response.json())
    ```
  </Tab>
</Tabs>

### Force roll forward

Immediately completes the rolling deployment, shifting all traffic to the candidate deployment. This works even if the deployment is in the process of rolling back.

<Warning>
  Force rolling forward may promote an under-provisioned deployment if the
  candidate has not finished scaling up.
</Warning>

<Tabs>
  <Tab title="cURL">
    ```bash Request theme={"system"}
    curl -X POST \
      https://api.baseten.co/v1/models/{model_id}/environments/production/force_roll_forward_promotion \
      -H "Authorization: Bearer $BASETEN_API_KEY"
    ```
  </Tab>

  <Tab title="Python">
    ```python Request theme={"system"}
    response = requests.post(
        "https://api.baseten.co/v1/models/{model_id}/environments/production/force_roll_forward_promotion",
        headers={"Authorization": f"Bearer {API_KEY}"},
    )

    print(response.json())
    ```
  </Tab>
</Tabs>

## Autoscaling during rolling deployments

For environments configured with autoscaling (`min_replica < max_replica`), Baseten continues to scale your deployment during a rolling deployment to meet traffic demand. Both the previous and candidate deployments scale up based on combined demand, and new capacity is distributed proportionally to the current traffic split. When demand drops, Baseten scales down both deployments the same way, removing replicas split by the current traffic ratio without changing the traffic split itself.

For example, with traffic split 60/40 between the previous and candidate deployments, an additional 10 replicas of demand provisions 6 replicas to the previous deployment and 4 to the candidate. A drop of 10 replicas removes 6 from the previous deployment and 4 from the candidate the same way.

A few constraints apply during the rolling deployment:

* Autoscaling adds and removes replicas throughout the rollout to track combined demand. Each deployment that is still part of the rollout keeps at least one replica, and the combined replica count stays within the environment's `min_replica` and `max_replica`.
* Capacity management continues during a `PAUSED` rolling deployment. Pausing stops the traffic shift, not capacity management. If demand changes while paused, both deployments still scale up or down.

## Dynamic replica admission

Rolling deployments adapt to candidate replicas as they become ready. Rather than assuming a full batch of replicas will be available immediately, Baseten adjusts the rollout based on live capacity.

For example, with 100 previous replicas and `max_unavailable_percent` set to `25`, Baseten requests 25 new replicas. If only 5 become ready, Baseten only removes 5 previous replicas to stay within your unavailable limit:

```text theme={"system"}
Max unavailable 25%
Requested:       Previous 75 replicas   Candidate 25 requested
Actually ready:  Previous 75 replicas   Candidate 5 ready
Next adjustment: Previous 70 replicas   Candidate 5 ready
```

The same adaptive behavior applies to `max_surge_percent`. With 100 previous replicas and a 25% surge limit, if only 5 of the 25 requested candidate replicas become ready, Baseten scales down 5 previous replicas before requesting the next batch. This ensures the rollout progresses based on actual ready capacity.

```text theme={"system"}
Max surge 25%
Requested:       Previous 100 replicas  Candidate 25 requested
Actually ready:  Previous 100 replicas  Candidate 5 ready
Next adjustment: Previous 95 replicas   Candidate 5 ready
```

In both modes, rollouts continue from live, ready capacity to ensure your environment remains stable throughout the transition.

## Environments without autoscaling

Environments where `min_replica == max_replica` have no autoscaling configured, so replica counts stay pinned during the rolling deployment. To pre-provision additional headroom for traffic spikes, set `replica_overhead_percent` to add replicas to the previous deployment before any traffic shifts. Use `stabilization_time_seconds` to wait between steps and monitor metrics before the next traffic shift.

## Deployment cleanup

After a rolling deployment completes, the `promotion_cleanup_strategy` setting controls what happens to the previous deployment.

* `SCALE_TO_ZERO`: Scales the previous deployment to zero replicas. It remains available for reactivation. This is the default.
* `KEEP`: Leaves the previous deployment running at its current replica count.
* `DEACTIVATE`: Deactivates the previous deployment. It stops serving traffic and releases all resources.

Set it alongside your other promotion settings:

<Tabs>
  <Tab title="cURL">
    ```bash Request theme={"system"}
    curl -X PATCH \
      https://api.baseten.co/v1/models/{model_id}/environments/production \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{
        "promotion_settings": {
          "promotion_cleanup_strategy": "DEACTIVATE"
        }
      }'
    ```
  </Tab>

  <Tab title="Python">
    ```python Request theme={"system"}
    response = requests.patch(
        "https://api.baseten.co/v1/models/{model_id}/environments/production",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "promotion_settings": {
                "promotion_cleanup_strategy": "DEACTIVATE"
            }
        },
    )

    print(response.json())
    ```
  </Tab>
</Tabs>
