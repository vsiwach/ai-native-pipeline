# Regional environments
Source: https://docs.baseten.co/deployment/regional-environments

Guarantee inference data stays in a specific geographic region with regional environments.

Regional environments route inference traffic for a deployment exclusively to workload planes within a designated geographic region. Use regional environments to meet data residency and compliance requirements, such as GDPR, without managing separate models per region.

<Note>
  Regional environments require initial configuration by Baseten.
  [Contact support](mailto:support@baseten.co) to set up regional restrictions for your environments.
</Note>

## How regional environments work

Regional environments build on [environments](/deployment/environments) and [restricted environments](/organization/restricted-environments) to add region-level routing guarantees. When Baseten configures regional restrictions for an environment, two things happen:

1. **Replicas are constrained** to workload planes within the designated region. Deployments promoted to that environment only run in the allowed region.
2. **A regional inference endpoint** becomes available that routes traffic directly to the region-specific workload plane, guaranteeing data stays in the designated region.

### Compare regional and standard endpoints

Standard environment endpoints don't guarantee regional routing.
Traffic may pass through a workload plane outside the intended region depending on DNS resolution.

Regional endpoints use a different URL format that maps directly to a region-specific workload plane:

| Endpoint type | URL format                                                                | Regional guarantee |
| :------------ | :------------------------------------------------------------------------ | :----------------- |
| Standard      | `https://model-{model_id}.api.baseten.co/environments/{env_name}/predict` | No                 |
| Regional      | `https://model-{model_id}-{env_name}.api.baseten.co/predict`              | Yes                |

The standard endpoint continues to function after you enable regional environments.
However, it doesn't guarantee that traffic stays within the restricted region.

<Warning>
  If you use regional environments, migrate your calling code to the regional endpoint to maintain compliance.
  The standard endpoint routes traffic through the original CNAME, which may point to a workload plane outside the restricted region.
</Warning>

### Call a regional endpoint

Regional endpoints accept the same request format as standard predict endpoints:

<Tabs>
  <Tab title="Python">
    Create an `httpx.Client` with the regional endpoint as the `base_url`. Reuse the client across requests for connection pooling. See [Configure HTTP clients](/inference/http-client-configuration) for recommended timeout and pool settings.

    ```python predict.py theme={"system"}
    import httpx
    import os

    model_id = "<your-model-id>"
    env_name = "prod-us"

    client = httpx.Client(
        base_url=f"https://model-{model_id}-{env_name}.api.baseten.co",
        headers={"Authorization": f"Bearer {os.environ['BASETEN_API_KEY']}"},
    )

    response = client.post("/predict", json={"prompt": "Hello, world!"})
    print(response.json())
    ```
  </Tab>

  <Tab title="cURL">
    Send a POST request to the regional endpoint with your API key in the `Authorization` header:

    ```sh Request theme={"system"}
    curl -X POST https://model-{model_id}-{env_name}.api.baseten.co/predict \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -H 'Content-Type: application/json' \
      -d '{"prompt": "Hello, world!"}'
    ```
  </Tab>

  <Tab title="Node.js">
    Use the built-in `fetch` API to call the regional endpoint. Replace `modelId` and `envName` with your model ID and environment name:

    ```javascript predict.js theme={"system"}
    const modelId = "<your-model-id>";
    const envName = "prod-us";

    const resp = await fetch(
      `https://model-${modelId}-${envName}.api.baseten.co/predict`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${process.env.BASETEN_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt: "Hello, world!" }),
      }
    );

    const data = await resp.json();
    console.log(data);
    ```
  </Tab>
</Tabs>

## Set up regional environments

1. **Create environments** with region-specific names (for example, `prod-us`, `prod-eu`, `staging-eu`). Use [restricted environments](/organization/restricted-environments) to control access.
2. **[Contact Baseten support](mailto:support@baseten.co)** to configure regional restrictions for your environments. We'll work with you to set them up per your required specs.
3. **Update your calling code** to use the regional endpoint format: `https://model-{model_id}-{env_name}.api.baseten.co/predict`.

### Environment naming requirements

Environment names used with regional environments must be valid DNS subdomain labels:

* Lowercase alphanumeric characters and hyphens only.
* Can't start or end with a hyphen.
* Maximum 40 characters.
* `development` is a reserved name and can't be used.

<Note>
  Regional environments apply across all models in a team. If you name an environment `prod-us` on one model, creating `prod-us` on another model in the same team applies the same regional restrictions.
</Note>

## Deploy to regional environments

Deploy and promote to regional environments the same way as standard environments:

```sh Terminal theme={"system"}
truss push --environment prod-us
```

Replicas spin up only in workload planes within the allowed region.

### Promotion behavior

When you promote a deployment to a regional environment, Baseten ensures regional restrictions are enforced. If the deployment was previously running without regional restrictions, a forced redeploy occurs to ensure compliance. This happens even when "turn off redeploy on promotion" is on for the model.

## Supported regions

Baseten can configure regional restrictions for a variety of geographic regions, including US, EU, UK, and Australia. [Contact support](mailto:support@baseten.co) to discuss your specific regional requirements.
