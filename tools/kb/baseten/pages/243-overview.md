# Overview
Source: https://docs.baseten.co/reference/inference-api/overview

Baseten provides two ways to call models: Model APIs for managed LLMs and deployed model endpoints for custom models and chains.

Every model running on Baseten is accessible over HTTPS through the inference API.
The API provides two paths depending on how your model is served.
Model APIs offer managed, high-performance LLMs through a single OpenAI-compatible endpoint, with no deployment step required.
Deployed model endpoints serve custom models and chains that you package and deploy with Truss, each routed through a dedicated subdomain.

## Model APIs

Model APIs give you instant access to popular open-source LLMs with optimized serving. Baseten manages the infrastructure (shared GPU clusters, model weights, and serving configuration), so there's no deployment step and nothing to configure. The supported catalog includes models like DeepSeek, GLM, and Kimi, with all models supporting tool calling and most supporting structured outputs. Pricing is per million tokens.

Because Model APIs implement the OpenAI chat completions format, switching from OpenAI to Baseten requires only changing the base URL and API key in your existing client. All requests route through a single endpoint:

```sh theme={"system"}
https://inference.baseten.co/v1/chat/completions
```

The [Chat Completions](/reference/inference-api/chat-completions) reference covers request and response schemas. For usage details including structured outputs and tool calling, refer to the [Model APIs guide](/inference/model-apis/overview).

## Deployed model endpoints

When you deploy a custom model or chain with Truss, Baseten assigns it a dedicated subdomain for routing. This is the path for models that aren't in the Model APIs catalog: models with custom serving logic, fine-tuned weights, or multi-step inference pipelines built as chains. You control the hardware, scaling behavior, and serving engine.

Each endpoint URL includes a deployment target: an environment name like `production`, the `development` deployment, or a specific deployment ID.

**For models:**

```
https://model-{model_id}.api.baseten.co/{deployment_type_or_id}/{endpoint}
```

**For chains:**

```
https://chain-{chain_id}.api.baseten.co/{deployment_type_or_id}/{endpoint}
```

* `model_id`: the model's alphanumeric ID, found in your model dashboard.
* `chain_id`: the chain's alphanumeric ID, found in your chain dashboard.
* `deployment_type_or_id`: either `development`, `production`, or a specific deployment's alphanumeric ID.
* `endpoint`: the API action, such as `predict`.

For [regional environments](/deployment/environments#regional-environments), the environment name is embedded in the hostname instead of the URL path:

```
https://model-{model_id}-{env_name}.api.baseten.co/{endpoint}
https://chain-{chain_id}-{env_name}.api.baseten.co/{endpoint}
```

For long-running tasks, the inference API supports [asynchronous inference](/inference/async) with priority queuing.

<Tip>
  The inference API [OpenAPI spec](https://api.baseten.co/inference-spec) is available for use with code generators, SDK tooling, and API clients.
</Tip>

### Predict endpoints

All predict endpoints accept a JSON request body that is forwarded directly to the model's `predict` function (for models) or chain entrypoint (for chains).

<Tabs>
  <Tab title="Models">
    | Method | Endpoint                                    | Description                                      |
    | :----- | :------------------------------------------ | :----------------------------------------------- |
    | `POST` | `/production/predict`                       | Call the **production** environment.             |
    | `POST` | `/environments/{env_name}/predict`          | Call a named **environment**.                    |
    | `POST` | `/development/predict`                      | Call the **development** deployment.             |
    | `POST` | `/deployment/{deployment_id}/predict`       | Call a specific **deployment**.                  |
    | `POST` | `/production/async_predict`                 | Async predict on **production**.                 |
    | `POST` | `/environments/{env_name}/async_predict`    | Async predict on a named **environment**.        |
    | `POST` | `/development/async_predict`                | Async predict on the **development** deployment. |
    | `POST` | `/deployment/{deployment_id}/async_predict` | Async predict on a specific **deployment**.      |
  </Tab>

  <Tab title="Chains">
    | Method | Endpoint                                       | Description                                   |
    | :----- | :--------------------------------------------- | :-------------------------------------------- |
    | `POST` | `/production/run_remote`                       | Call the **production** environment.          |
    | `POST` | `/environments/{env_name}/run_remote`          | Call a named **environment**.                 |
    | `POST` | `/development/run_remote`                      | Call the **development** deployment.          |
    | `POST` | `/deployment/{deployment_id}/run_remote`       | Call a specific **deployment**.               |
    | `POST` | `/production/async_run_remote`                 | Async call on **production**.                 |
    | `POST` | `/environments/{env_name}/async_run_remote`    | Async call on a named **environment**.        |
    | `POST` | `/development/async_run_remote`                | Async call on the **development** deployment. |
    | `POST` | `/deployment/{deployment_id}/async_run_remote` | Async call on a specific **deployment**.      |
  </Tab>

  <Tab title="Regional">
    Regional endpoints use bare paths on regional hostnames (`model-{model_id}-{env_name}.api.baseten.co`).

    | Method | Endpoint            | Description             |
    | :----- | :------------------ | :---------------------- |
    | `POST` | `/predict`          | Synchronous predict.    |
    | `POST` | `/run_remote`       | Synchronous chain call. |
    | `POST` | `/async_predict`    | Async predict.          |
    | `POST` | `/async_run_remote` | Async chain call.       |
  </Tab>
</Tabs>

### Status endpoints

| Method   | Endpoint                                         | Description                                      |
| :------- | :----------------------------------------------- | :----------------------------------------------- |
| `GET`    | `/async_request/{request_id}`                    | Get the status of an async request.              |
| `DELETE` | `/async_request/{request_id}`                    | Cancel a queued async request.                   |
| `GET`    | `/production/async_queue_status`                 | Queue status for **production**.                 |
| `GET`    | `/environments/{env_name}/async_queue_status`    | Queue status for a named **environment**.        |
| `GET`    | `/development/async_queue_status`                | Queue status for the **development** deployment. |
| `GET`    | `/deployment/{deployment_id}/async_queue_status` | Queue status for a specific **deployment**.      |
| `GET`    | `/async_queue_status`                            | Queue status (regional).                         |

### Wake endpoints

| Method | Endpoint                           | Description                          |
| :----- | :--------------------------------- | :----------------------------------- |
| `POST` | `/production/wake`                 | Wake the **production** environment. |
| `POST` | `/environments/{env_name}/wake`    | Wake a named **environment**.        |
| `POST` | `/development/wake`                | Wake the **development** deployment. |
| `POST` | `/deployment/{deployment_id}/wake` | Wake a specific **deployment**.      |
| `POST` | `/wake`                            | Wake (regional).                     |

### Timeouts

Each request to a deployed model or chain has a server-side timeout. Requests that exceed it return a `504`.

| Surface                                                      | Default timeout           |
| :----------------------------------------------------------- | :------------------------ |
| Sync predict (`/predict`, `/run_remote`)                     | 1200 seconds (20 minutes) |
| Async predict submit (`/async_predict`, `/async_run_remote`) | 3600 seconds (60 minutes) |
| Wake (`/wake`)                                               | 600 seconds (10 minutes)  |

Timeouts aren't user-configurable. Set client timeouts based on your model's expected response time. For more information, see [Configure HTTP clients](/inference/http-client-configuration#set-timeouts). For how to interpret and respond to a `504`, see [Inference errors](/inference/errors#504-gateway-timeout).

### Request size

The ingress proxy caps each inbound request body at **100 MB**. Requests that exceed this limit are rejected at the edge with a `413 Request Entity Too Large` before they reach your model or chain. The limit applies to the full HTTP body, including JSON envelope and any base64-encoded media, and is not user-configurable.

For payloads that approach or exceed this cap (large audio files, long video clips, batched media), upload the file to your own object storage (S3, GCS, Azure Blob) and send a [pre-signed URL](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ShareObjectPreSignedURL.html) in the request body instead of inlining the bytes. The model fetches the file directly from storage, keeping the request body small and avoiding retry storms on large uploads.

For how to interpret and respond to a `413`, including the separate async payload limit, see [Inference errors](/inference/errors#413-payload-too-large).
