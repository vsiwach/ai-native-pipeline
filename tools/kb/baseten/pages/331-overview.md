# Overview
Source: https://docs.baseten.co/reference/management-api/overview

Manage models and deployments with the Baseten management API. It supports monitoring, CI/CD, and automation at both the model and workspace levels.

The full OpenAPI spec is available at [api.baseten.co/v1/spec](https://api.baseten.co/v1/spec) for generating API clients.

Management API requests are rate limited per API key. See [Rate limits](/reference/management-api/rate-limits) for the per-endpoint limits and how to handle `429` responses.

To deploy a model archive programmatically, see [Create a model with the REST API](/examples/create-a-model-with-rest).

## Model endpoints

| Method | Endpoint                                                                            | Description                  |
| :----- | :---------------------------------------------------------------------------------- | :--------------------------- |
| `GET`  | [`/v1/models`](/reference/management-api/models/gets-all-models)                    | Get all models               |
| `GET`  | [`/v1/models/{model_id}`](/reference/management-api/models/gets-a-model-by-id)      | Get models by ID             |
| `POST` | [`/v1/prepare_model_upload`](/reference/management-api/models/prepare-model-upload) | Prepare a model upload       |
| `POST` | [`/v1/models`](/reference/management-api/models/creates-a-model-from-a-source)      | Create a model from a source |
| `DEL`  | [`/v1/models/{model_id}`](/reference/management-api/models/deletes-a-model-by-id)   | Delete models                |

## Chain endpoints

| Method | Endpoint                                                                          | Description       |
| :----- | :-------------------------------------------------------------------------------- | :---------------- |
| `GET`  | [`/v1/chains`](/reference/management-api/chains/gets-all-chains)                  | Get all Chains    |
| `GET`  | [`/v1/chains/{chain_id}`](/reference/management-api/chains/gets-a-chain-by-id)    | Get a Chain by ID |
| `DEL`  | [`/v1/chains/{chain_id}`](/reference/management-api/chains/deletes-a-chain-by-id) | Delete Chains     |

## Deployment endpoints

<Tabs>
  <Tab title="Models">
    ### Activate a model deployment

    | Method | Endpoint                                                                                                                                                         | Description                 |
    | :----- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------- |
    | `POST` | [`/v1/models/{model_id}/environments/{env_name}/activate`](/reference/management-api/deployments/activate/activates-a-deployment-associated-with-an-environment) | **Activate** an environment |
    | `POST` | [`/v1/models/{model_id}/deployments/development/activate`](/reference/management-api/deployments/activate/activates-a-development-deployment)                    | **Activate** development    |
    | `POST` | [`/v1/models/{model_id}/deployments/{deployment_id}/activate`](/reference/management-api/deployments/activate/activates-a-deployment)                            | **Activate** a deployment   |
    | `POST` | [`/v1/models/{model_id}/deployments/production/activate`](/reference/management-api/deployments/activate/activates-production-deployment)                        | **Activate** production     |

    ### Deactivate a model deployment

    | Method | Endpoint                                                                                                                                                               | Description                   |
    | :----- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------- |
    | `POST` | [`/v1/models/{model_id}/environments/{env_name}/deactivate`](/reference/management-api/deployments/deactivate/deactivates-a-deployment-associated-with-an-environment) | **Deactivate** an environment |
    | `POST` | [`/v1/models/{model_id}/deployments/development/deactivate`](/reference/management-api/deployments/deactivate/deactivates-a-development-deployment)                    | **Deactivate** development    |
    | `POST` | [`/v1/models/{model_id}/deployments/{deployment_id}/deactivate`](/reference/management-api/deployments/deactivate/deactivates-a-deployment)                            | **Deactivate** a deployment   |
    | `POST` | [`/v1/models/{model_id}/deployments/production/deactivate`](/reference/management-api/deployments/deactivate/deactivates-production-deployment)                        | **Deactivate** production     |

    ### Retry a model deployment

    | Method | Endpoint                                                                                                                              | Description            |
    | :----- | :------------------------------------------------------------------------------------------------------------------------------------ | :--------------------- |
    | `POST` | [`/v1/models/{model_id}/deployments/development/retry`](/reference/management-api/deployments/retry/retries-a-development-deployment) | **Retry** development  |
    | `POST` | [`/v1/models/{model_id}/deployments/{deployment_id}/retry`](/reference/management-api/deployments/retry/retries-a-deployment)         | **Retry** a deployment |
    | `POST` | [`/v1/models/{model_id}/deployments/production/retry`](/reference/management-api/deployments/retry/retries-production-deployment)     | **Retry** production   |

    ### Promote a model deployment

    | Method | Endpoint                                                                                                                                                   | Description                              |
    | :----- | :--------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------- |
    | `POST` | [`/v1/models/{model_id}/environments/{env_name}/promote`](/reference/management-api/deployments/promote/promotes-a-deployment-to-an-environment)           | **Promote** to model **environment**     |
    | `POST` | [`/v1/models/{model_id}/environments/{env_name}/cancel_promotion`](/reference/management-api/deployments/promote/cancel-promotion)                         | **Cancel** a promotion to an environment |
    | `POST` | [`/v1/models/{model_id}/deployments/development/promote`](/reference/management-api/deployments/promote/promotes-a-development-deployment-to-production)   | **Promote** development deployment       |
    | `POST` | [`/v1/models/{model_id}/deployments/{deployment_id}/promote`](/reference/management-api/deployments/promote/promotes-a-deployment-to-production)           | **Promote** any deployment               |
    | `POST` | [`/v1/models/{model_id}/environments/{env_name}/pause_promotion`](/reference/management-api/deployments/promote/pause-promotion)                           | **Pause** rolling deployment             |
    | `POST` | [`/v1/models/{model_id}/environments/{env_name}/resume_promotion`](/reference/management-api/deployments/promote/resume-promotion)                         | **Resume** rolling deployment            |
    | `POST` | [`/v1/models/{model_id}/environments/{env_name}/force_cancel_promotion`](/reference/management-api/deployments/promote/force-cancel-promotion)             | **Force cancel** rolling deployment      |
    | `POST` | [`/v1/models/{model_id}/environments/{env_name}/force_roll_forward_promotion`](/reference/management-api/deployments/promote/force-roll-forward-promotion) | **Force roll forward** promotion         |

    ### Autoscaling

    | Method  | Endpoint                                                                                                                                                       | Description                                     |
    | :------ | :------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------- |
    | `PATCH` | [`.../deployments/development/autoscaling_settings`](/reference/management-api/deployments/autoscaling/updates-a-development-deployments-autoscaling-settings) | Updates **development's autoscaling** settings  |
    | `PATCH` | [`.../deployments/{deployment_id}/autoscaling_settings`](/reference/management-api/deployments/autoscaling/updates-a-deployments-autoscaling-settings)         | Updates a **deployment's autoscaling** settings |
    | `PATCH` | [`.../deployments/production/autoscaling_settings`](/reference/management-api/deployments/autoscaling/updates-production-deployment-autoscaling-settings)      | Updates **production's autoscaling** settings   |

    ### Manage deployment endpoints

    | Method | Endpoint                                                                                                                                         | Description                       |
    | :----- | :----------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------- |
    | `POST` | [`/v1/models/{model_id}/deployments`](/reference/management-api/deployments/adds-a-deployment-to-a-model)                                        | Add a deployment to a model       |
    | `GET`  | [`/v1/models/{model_id}/deployments`](/reference/management-api/deployments/gets-all-deployments-of-a-model)                                     | Get all model deployments         |
    | `GET`  | [`/v1/models/{model_id}/deployments/production`](/reference/management-api/deployments/gets-a-models-production-deployment)                      | Production model deployment       |
    | `GET`  | [`/v1/models/{model_id}/deployments/development`](/reference/management-api/deployments/gets-a-models-development-deployment)                    | Development model deployment      |
    | `GET`  | [`/v1/models/{model_id}/deployments/{deployment_id}`](/reference/management-api/deployments/gets-a-models-deployment-by-id)                      | Any model deployment by ID        |
    | `GET`  | [`/v1/models/{model_id}/deployments/{deployment_id}/logs`](/reference/management-api/deployments/get-deployment-logs)                            | Get model deployment logs         |
    | `GET`  | [`/v1/models/{model_id}/deployments/{deployment_id}/metrics`](/reference/management-api/deployments/get-deployment-metrics)                      | Get model deployment metrics      |
    | `GET`  | [`/v1/models/{model_id}/deployments/{deployment_id}/config`](/reference/management-api/deployments/get-deployment-config)                        | Get model deployment config       |
    | `GET`  | [`/v1/models/{model_id}/deployments/{deployment_id}/download`](/reference/management-api/deployments/get-deployment-download-url)                | Get model deployment download URL |
    | `DEL`  | [`/v1/models/{model_id}/deployments/{deployment_id}`](/reference/management-api/deployments/deletes-a-models-deployment-by-id)                   | Delete model deployments          |
    | `DEL`  | [`/v1/models/{model_id}/deployments/{deployment_id}/replicas/{replica_id}`](/reference/management-api/deployments/terminates-deployment-replica) | Terminate deployment replica      |
  </Tab>

  <Tab title="Chains">
    ### Deactivate a Chain deployment

    | Method | Endpoint                                                                                                                                                | Description                       |
    | :----- | :------------------------------------------------------------------------------------------------------------------------------------------------------ | :-------------------------------- |
    | `POST` | [`/v1/chains/{chain_id}/deployments/{chain_deployment_id}/deactivate`](/reference/management-api/deployments/deactivate/deactivates-a-chain-deployment) | **Deactivate** a Chain deployment |

    ### Promote a Chain deployment

    | Method | Endpoint                                                                                                                                               | Description                  |
    | :----- | :----------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------- |
    | `POST` | [`/v1/chains/{chain_id}/environments/{env_name}/promote`](/reference/management-api/deployments/promote/promotes-a-chain-deployment-to-an-environment) | Promote to chain environment |

    ### Autoscaling

    | Method  | Endpoint                                                                                                                                              | Description                                            |
    | :------ | :---------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------- |
    | `PATCH` | [`.../chainlet_settings/autoscaling_settings`](/reference/management-api/deployments/autoscaling/update-a-chainlet-environments-autoscaling-settings) | **Update chainlet** environment's autoscaling settings |

    ### Manage Chain deployments

    | Method | Endpoint                                                                                                                            | Description                  |
    | :----- | :---------------------------------------------------------------------------------------------------------------------------------- | :--------------------------- |
    | `GET`  | [`/v1/chains/{chain_id}/deployments`](/reference/management-api/deployments/gets-all-chain-deployments)                             | Get all chain deployments    |
    | `GET`  | [`/v1/chains/{chain_id}/deployments/{chain_deployment_id}`](/reference/management-api/deployments/gets-a-chain-deployment-by-id)    | Any chain deployment by ID   |
    | `DEL`  | [`/v1/chains/{chain_id}/deployments/{chain_deployment_id}`](/reference/management-api/deployments/deletes-a-chain-deployment-by-id) | **Delete** chain deployments |
  </Tab>
</Tabs>

## Environment endpoints

<Tabs>
  <Tab title="Models">
    | Method  | Endpoint                                                                                                                  | Description                |
    | :------ | :------------------------------------------------------------------------------------------------------------------------ | :------------------------- |
    | `POST`  | [`/v1/models/{model_id}/environments`](/reference/management-api/environments/create-an-environment)                      | Create environment         |
    | `GET`   | [`/v1/models/{model_id}/environments`](/reference/management-api/environments/get-all-environments)                       | Get all environments       |
    | `GET`   | [`/v1/models/{model_id}/environments/{env_name}`](/reference/management-api/environments/get-an-environments-details)     | Get an environment details |
    | `PATCH` | [`/v1/models/{model_id}/environments/{env_name}`](/reference/management-api/environments/update-an-environments-settings) | Update model environment   |
  </Tab>

  <Tab title="Chains">
    | Method  | Endpoint                                                                                                                                                                                | Description                                 |
    | :------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------ |
    | `POST`  | [`/v1/chains/{chain_id}/environments`](/reference/management-api/environments/create-a-chain-environment)                                                                               | Create chain environment                    |
    | `GET`   | [`/v1/chains/{chain_id}/environments`](/reference/management-api/environments/get-all-chain-environments)                                                                               | Get all chain environments                  |
    | `GET`   | [`/v1/chains/{chain_id}/environments/{env_name}`](/reference/management-api/environments/get-a-chain-environments-details)                                                              | Get a chain environment                     |
    | `PATCH` | [`/v1/chains/{chain_id}/environments/{env_name}`](/reference/management-api/environments/update-a-chain-environments-settings)                                                          | Update chain environment                    |
    | `POST`  | [`/v1/chains/{chain_id}/environments/{env_name}/chainlet_settings/instance_types/update`](/reference/management-api/environments/update-a-chainlet-environments-instance-type-settings) | Update chainlet environment's instance type |
  </Tab>
</Tabs>

## Instance type endpoints

| Method | Endpoint                                                                                         | Description              |
| :----- | :----------------------------------------------------------------------------------------------- | :----------------------- |
| `GET`  | [`/v1/instance_types`](/reference/management-api/instance-types/gets-all-instance-types)         | Get all instance types   |
| `GET`  | [`/v1/instance_type_prices`](/reference/management-api/instance-types/gets-instance-type-prices) | Get instance type prices |

## Model API endpoints

| Method | Endpoint                                                                                           | Description             |
| :----- | :------------------------------------------------------------------------------------------------- | :---------------------- |
| `GET`  | [`/v1/model_apis`](/reference/management-api/model-apis/gets-all-model-apis)                       | List Model APIs         |
| `GET`  | [`/v1/model_apis/{model_api_name}`](/reference/management-api/model-apis/gets-a-model-api-by-name) | Get a Model API by name |

## Team endpoints

| Method | Endpoint                                                       | Description   |
| :----- | :------------------------------------------------------------- | :------------ |
| `GET`  | [`/v1/teams`](/reference/management-api/teams/lists-all-teams) | Get all teams |

## Secret endpoints

| Method | Endpoint                                                                               | Description                    |
| :----- | :------------------------------------------------------------------------------------- | :----------------------------- |
| `GET`  | [`/v1/secrets`](/reference/management-api/secrets/gets-all-secrets)                    | Get all secrets                |
| `POST` | [`/v1/secrets`](/reference/management-api/secrets/upserts-a-secret)                    | Create or update a secret      |
| `GET`  | [`/v1/teams/{team_id}/secrets`](/reference/management-api/teams/gets-all-team-secrets) | Get all team secrets           |
| `POST` | [`/v1/teams/{team_id}/secrets`](/reference/management-api/teams/upserts-a-team-secret) | Create or update a team secret |

## API Key endpoints

| Method   | Endpoint                                                                                 | Description           |
| :------- | :--------------------------------------------------------------------------------------- | :-------------------- |
| `GET`    | [`/v1/api_keys`](/reference/management-api/api-keys/lists-the-users-api-keys)            | Get all API keys      |
| `POST`   | [`/v1/api_keys`](/reference/management-api/api-keys/creates-an-api-key)                  | Create an API key     |
| `DELETE` | [`/v1/api_keys/{api_key_prefix}`](/reference/management-api/api-keys/delete-an-api-key)  | Delete an API key     |
| `POST`   | [`/v1/teams/{team_id}/api_keys`](/reference/management-api/teams/creates-a-team-api-key) | Create a team API key |

## Billing endpoints

| Method | Endpoint                                                                                                     | Description               |
| :----- | :----------------------------------------------------------------------------------------------------------- | :------------------------ |
| `GET`  | [`/v1/billing/usage_summary`](/reference/management-api/billing/gets-billing-usage-summary-for-a-date-range) | Get billing usage summary |

## Training endpoints

For a complete reference and request schemas, see the [Training API overview](/reference/training-api/overview).

### Training projects

| Method   | Endpoint                                                                                                                  | Description                        |
| :------- | :------------------------------------------------------------------------------------------------------------------------ | :--------------------------------- |
| `GET`    | [`/v1/training_projects`](/reference/training-api/get-training-projects)                                                  | List all training projects         |
| `POST`   | [`/v1/training_projects`](/reference/training-api/create-training-project)                                                | Create a training project          |
| `GET`    | [`/v1/training_projects/{training_project_id}`](/reference/training-api/get-training-project)                             | Get a training project             |
| `DELETE` | [`/v1/training_projects/{training_project_id}`](/reference/training-api/delete-training-project)                          | Delete a training project          |
| `POST`   | [`/v1/teams/{team_id}/training_projects`](/reference/management-api/teams/creates-a-team-training-project)                | Create a team training project     |
| `GET`    | [`/v1/training_projects/{training_project_id}/cache/summary`](/reference/training-api/get-training-project-cache-summary) | Get training project cache summary |

### Training jobs

| Method   | Endpoint                                                                                                                                           | Description                       |
| :------- | :------------------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------- |
| `POST`   | [`/v1/training_projects/{training_project_id}/jobs`](/reference/training-api/create-training-job)                                                  | Create a training job             |
| `GET`    | [`/v1/training_projects/{training_project_id}/jobs`](/reference/training-api/list-training-jobs)                                                   | List all jobs in a project        |
| `GET`    | [`/v1/training_projects/{training_project_id}/jobs/{training_job_id}`](/reference/training-api/get-training-job)                                   | Get a training job by ID          |
| `DELETE` | [`/v1/training_projects/{training_project_id}/jobs/{training_job_id}`](/reference/training-api/delete-training-job)                                | Delete a training job             |
| `POST`   | [`/v1/training_projects/{training_project_id}/jobs/{training_job_id}/stop`](/reference/training-api/stop-training-job)                             | Stop a training job               |
| `POST`   | [`/v1/training_projects/{training_project_id}/jobs/{training_job_id}/recreate`](/reference/training-api/recreate-training-job)                     | Recreate a training job           |
| `GET`    | [`/v1/training_projects/{training_project_id}/jobs/{training_job_id}/logs`](/reference/training-api/get-training-job-logs)                         | Get training job logs             |
| `GET`    | [`/v1/training_projects/{training_project_id}/jobs/{training_job_id}/metrics`](/reference/training-api/get-training-job-metrics)                   | Get training job metrics          |
| `GET`    | [`/v1/training_projects/{training_project_id}/jobs/{training_job_id}/checkpoints`](/reference/training-api/get-training-job-checkpoints)           | List job checkpoints              |
| `GET`    | [`/v1/training_projects/{training_project_id}/jobs/{training_job_id}/checkpoint_files`](/reference/training-api/get-training-job-checkpoint-files) | Get checkpoint files              |
| `GET`    | [`/v1/training_projects/{training_project_id}/jobs/{training_job_id}/download`](/reference/training-api/download-training-job)                     | Download training job artifacts   |
| `GET`    | [`/v1/training_projects/{training_project_id}/jobs/{training_job_id}/auth_codes`](/reference/training-api/get-auth-codes-for-training-job)         | Get auth codes for a training job |
| `POST`   | [`/v1/training_jobs/search`](/reference/training-api/search-training-jobs)                                                                         | Search across all training jobs   |

## Frontier Gateway endpoints

For the conceptual guide and end-to-end examples, see the [Frontier Gateway overview](/frontier-gateway/overview).

### Endpoints

| Method   | Endpoint                                                                                       | Description        |
| :------- | :--------------------------------------------------------------------------------------------- | :----------------- |
| `POST`   | [`/v1/gateway/endpoints`](/reference/gateway/endpoints/create-an-endpoint)                     | Create an endpoint |
| `GET`    | [`/v1/gateway/endpoints`](/reference/gateway/endpoints/list-endpoints)                         | List endpoints     |
| `GET`    | [`/v1/gateway/endpoints/{endpoint_id}`](/reference/gateway/endpoints/get-an-endpoint)          | Get an endpoint    |
| `PATCH`  | [`/v1/gateway/endpoints/{endpoint_id}`](/reference/gateway/endpoints/replace-endpoint-targets) | Update an endpoint |
| `DELETE` | [`/v1/gateway/endpoints/{endpoint_id}`](/reference/gateway/endpoints/delete-an-endpoint)       | Delete an endpoint |

### Groups

| Method   | Endpoint                                                                    | Description    |
| :------- | :-------------------------------------------------------------------------- | :------------- |
| `POST`   | [`/v1/gateway/groups`](/reference/gateway/groups/create-a-group)            | Create a group |
| `GET`    | [`/v1/gateway/groups`](/reference/gateway/groups/list-groups)               | List groups    |
| `GET`    | [`/v1/gateway/groups/{group_id}`](/reference/gateway/groups/get-a-group)    | Get a group    |
| `PATCH`  | [`/v1/gateway/groups/{group_id}`](/reference/gateway/groups/update-a-group) | Update a group |
| `DELETE` | [`/v1/gateway/groups/{group_id}`](/reference/gateway/groups/delete-a-group) | Delete a group |

### API keys

| Method   | Endpoint                                                                                                   | Description               |
| :------- | :--------------------------------------------------------------------------------------------------------- | :------------------------ |
| `POST`   | [`/v1/gateway/groups/{group_id}/api_keys`](/reference/gateway/api-keys/create-an-api-key)                  | Create an API key         |
| `GET`    | [`/v1/gateway/groups/{group_id}/api_keys`](/reference/gateway/api-keys/list-api-keys-for-a-group)          | List API keys for a group |
| `GET`    | [`/v1/gateway/groups/{group_id}/api_keys/{api_key_prefix}`](/reference/gateway/api-keys/get-an-api-key)    | Get an API key            |
| `DELETE` | [`/v1/gateway/groups/{group_id}/api_keys/{api_key_prefix}`](/reference/gateway/api-keys/revoke-an-api-key) | Revoke an API key         |
