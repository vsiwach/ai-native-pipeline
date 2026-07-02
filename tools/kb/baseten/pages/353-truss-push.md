# truss.push
Source: https://docs.baseten.co/reference/sdk/truss/push



Deploys a **Truss** model to Baseten.

**Parameters:**

| Name                                      | Type                         | Description                                                                                                                                                                                                     |
| ----------------------------------------- | ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `target_directory`                        | *str*                        | Path to the Truss directory to push.                                                                                                                                                                            |
| `remote`                                  | *Optional\[str]*             | Name of the remote in `.trussrc` to push to.                                                                                                                                                                    |
| `model_name`                              | *Optional\[str]*             | Temporarily override the model name for this deployment without updating `config.yaml`.                                                                                                                         |
| `publish`                                 | *bool*                       | Deploy as **published**. If no production deployment exists, promote it to production.                                                                                                                          |
| `promote`                                 | *bool*                       | Deploy as **published** and promote to production, even if a production deployment exists.                                                                                                                      |
| `preserve_previous_production_deployment` | *bool*                       | Preserve the previous production deployment's **autoscaling settings** (only with `promote`).                                                                                                                   |
| `trusted`                                 | *Optional\[bool]*            | **Deprecated.** All models are trusted by default. This parameter is ignored.                                                                                                                                   |
| `disable_truss_download`                  | *bool*                       | Disable downloading of the Truss directory from the UI.                                                                                                                                                         |
| `deployment_name`                         | *Optional\[str]*             | Custom deployment name (alphanumeric, `.`, `-`, or `_` only). Requires `publish` or `promote`.                                                                                                                  |
| `environment`                             | *Optional\[str]*             | Name of a stable environment to deploy to.                                                                                                                                                                      |
| `include_git_info`                        | *bool*                       | Attach git versioning info (sha, branch, tag) to deployments made from within a git repo. Defaults to `False`.                                                                                                  |
| `preserve_env_instance_type`              | *bool*                       | When deploying to an `environment`, whether to resolve the instance type from the Truss config's `resources` (`False`) or preserve the instance type already configured on the environment. Defaults to `True`. |
| `deploy_timeout_minutes`                  | *Optional\[int]*             | Timeout in minutes for the deployment operation.                                                                                                                                                                |
| `labels`                                  | *Optional\[Dict\[str, Any]]* | JSON-serializable dictionary of label key-value pairs to attach to the deployment.                                                                                                                              |
| `team`                                    | *Optional\[str]*             | Name of the team to push the model to.                                                                                                                                                                          |
