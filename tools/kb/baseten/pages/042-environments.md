# Environments
Source: https://docs.baseten.co/deployment/environments

Manage your model's release cycles with environments.

Environments provide structured management for deployments, ensuring controlled rollouts, stable endpoints, and autoscaling. They help teams stage, test, and release models without affecting production traffic.

<img />

Deployments can be promoted to an environment (for example, "staging") to validate outputs before moving to production, allowing for safer model iteration and evaluation.

## Deployment management

Environments support structured validation before promoting a deployment, including:

* Automated tests and evaluations.
* Manual testing in pre-production.
* Gradual traffic shifts with canary deployments.
* Shadow serving for real-world analysis.

Promoting a deployment ensures it inherits environment-specific scaling and monitoring settings:

* Dedicated API endpoint: See the [Predict API reference](/reference/inference-api/overview#predict-endpoints).
* Autoscaling controls: Scale behavior is managed per environment.
* Traffic ramp-up: Supports [rolling deployments](/deployment/rolling-deployments) for incremental traffic shifting.
* Monitoring and metrics: scope [logs](/observability/logs#scope-by-environment-or-deployment) and [metrics](/observability/metrics) to the environment in the dashboard, or [export environment metrics](/observability/export-metrics/overview) to your own observability stack.

The production environment operates like any other environment but has restrictions:

* It can't be deleted unless the entire model is removed.
* You can't create additional environments named "production."

## Custom environments

In addition to the standard production environment, you can create as many custom environments as needed:

1. In the model management page on the Baseten dashboard.
2. Through the [create environment endpoint](/reference/management-api/environments/create-an-environment) in the management API.

## Deployment promotion

When you promote a deployment to an environment, Baseten associates the deployment with that environment and applies the environment's autoscaling settings. If the deployment can be reused directly, promotion completes without creating new resources. Otherwise, Baseten creates a new deployment with a unique ID, initializes its resources, and replaces the existing deployment in that environment.

A new deployment is created when:

* The deployment is already associated with another environment.
* The environment has a different instance type or resource profile.
* [Re-deploy on promotion](#re-deploy-on-promotion) is enabled.

If a previous deployment existed in the environment, the new one inherits its autoscaling settings and the old deployment is demoted.

In every case, promotion reuses the image the deployment was already built with. Even when Baseten creates a new deployment, it copies that existing image rather than rebuilding or re-pulling your base image.

### Published deployment promotion

If a published deployment (not a development deployment) is promoted, its autoscaling settings are updated to match the environment.

Previous deployments are demoted but remain in the system.

## Direct deployment to an environment

You can deploy directly to a named environment by specifying `--environment` in `truss push`:

```sh Terminal theme={"system"}
cd my_model/
truss push --environment {environment_name}
```

<Note>Only one active promotion per environment is allowed at a time.</Note>

## Environment access in code

The environment name is available in `model.py` through the `environment` keyword argument:

```python model/model.py theme={"system"}
def __init__(self, **kwargs):
    self._environment = kwargs["environment"]
```

You can use the environment in your `load()` method to configure per-environment behavior:

```python model/model.py theme={"system"}
def load(self):
    if self._environment.get("name") == "production":
        self.setup_sentry()
        self.model = self.load_production_weights()
    else:
        self.model = self.load_default_weights()
```

If you use environment-specific configuration in `load()`, you'll need to enable re-deploy on promotion to ensure the environment is correctly initialized after each promotion. See [Re-deploy on promotion](#re-deploy-on-promotion) for details.

<Note>
  The `environment` keyword argument is only available to Python Truss models. Custom servers read the environment name from the filesystem instead. See [Environment name](/development/model/custom-server#environment-name).
</Note>

## Re-deploy on promotion

By default, promoting a deployment reuses the existing deployment when possible. This is the fastest promotion path, but it means `load()` doesn't re-run. Any environment-specific configuration set during the original `load()` call persists, even if the deployment moves to a different environment.

You can configure an environment to create a fresh deployment every time you promote to it. The new deployment reuses the same image and re-runs `load()` with the target environment's context, so environment-specific configuration takes effect.

Enable this if your `load()` method uses `kwargs["environment"]` to configure per-environment behavior, or if you promote the same source deployment to multiple environments and want each to get a fresh deployment.

Toggle **Re-deploy when promoting** in the environment settings on your model's page in the Baseten dashboard, or set it through the [update environment settings endpoint](/reference/management-api/environments/update-an-environments-settings).

<Note>
  If you promote a deployment that's already associated with an environment, Baseten creates a new deployment regardless of this setting.
</Note>

## Regional environments

Regional environments restrict inference traffic to a specific geographic region for data residency compliance. When your organization enables regional environments, each environment gets a dedicated regional endpoint that routes directly to infrastructure in the designated region.

<Note>
  Your Baseten account team configures regional environments at the organization level. Contact them to enable regional environments.
</Note>

### Regional endpoint format

Regional endpoints embed the environment name in the hostname instead of the URL path:

<Tabs>
  <Tab title="Model">
    Call a model's regional endpoint with `/predict` or `/async_predict`.

    ```
    https://model-{model_id}-{env_name}.api.baseten.co/predict
    ```

    For example, a model with ID `abc123` in the `prod-us` environment:

    ```
    https://model-abc123-prod-us.api.baseten.co/predict
    ```
  </Tab>

  <Tab title="Chain">
    Call a chain's regional endpoint with `/run_remote` or `/async_run_remote`.

    ```
    https://chain-{chain_id}-{env_name}.api.baseten.co/run_remote
    ```
  </Tab>

  <Tab title="WebSocket">
    Connect to a regional WebSocket endpoint for models or chains.

    ```
    wss://model-{model_id}-{env_name}.api.baseten.co/websocket
    wss://chain-{chain_id}-{env_name}.api.baseten.co/websocket
    ```
  </Tab>

  <Tab title="gRPC">
    Connect to a regional gRPC endpoint using the `grpc.api.baseten.co` subdomain.

    ```
    model-{model_id}-{env_name}.grpc.api.baseten.co:443
    ```
  </Tab>
</Tabs>

The regional endpoint URL appears in your model's API endpoint section in the Baseten dashboard once your organization has regional environments enabled.

### API restrictions on regional endpoints

Regional endpoints derive the environment exclusively from the hostname. Path-based routing (`/environments/`, `/production/`, `/deployment/`) is rejected. For gRPC, don't set `x-baseten-environment` or `x-baseten-deployment` metadata headers.

## Environment deletion

You can delete environments, except for production. To remove a production deployment, first promote another deployment to production or delete the entire model.

* Deleted environments are removed from the overview but remain in billing history.
* They don't consume resources after deletion.
* API requests to a deleted environment return a 404 error.

<Warning>Deletion is permanent. Consider deactivation instead.</Warning>
