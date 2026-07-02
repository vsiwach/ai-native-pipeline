# Create an endpoint
Source: https://docs.baseten.co/reference/gateway/endpoints/create-an-endpoint

POST https://api.baseten.co/v1/gateway/endpoints
Create a Frontier Gateway endpoint: a routing slug and the Baseten deployment it points to.

Create an endpoint. An endpoint is a globally-unique routing slug plus the target it points to. Once created, requests that reach the gateway with this slug route to the target you specify. For the conceptual walkthrough, see [Endpoints](/frontier-gateway/endpoints).

### Authentication

<ParamField type="string">
  Workspace API key with management scope, passed as `Authorization: Api-Key $BASETEN_API_KEY` (or `Bearer`; both are accepted).
</ParamField>

### Body

<ParamField type="string">
  Globally-unique routing slug, formatted `{org_prefix}/{name}`. The `org_prefix` must be a prefix your organization owns, registered by the Baseten team during onboarding. Both segments are URL-safe. You can change the slug later with [Update an endpoint](/reference/gateway/endpoints/replace-endpoint-targets).
</ParamField>

<ParamField type="object[]">
  The endpoint's upstream targets. Exactly one target is supported at this time: send a list of length one. Sending an empty list or more than one target returns `400`.

  Each entry takes:

  * **`provider`** (`string`, required): Upstream provider for the target. One of `BASETEN`, `ANTHROPIC`, or `OPENAI`.
  * **`model_id`** (`string`): The Baseten model the slug routes to. Use for `BASETEN` targets.
  * **`environment_name`** (`string`): Baseten model environment to route to. Only valid for `BASETEN` targets. Omit it, or pass `production`, to target production.
  * **`secret_id`** (`string`): Baseten secret holding the provider credential. Required for external providers (`ANTHROPIC`, `OPENAI`).
  * **`target_model`** (`string`): Upstream model name to send. Required for external providers; optional for `BASETEN`.
</ParamField>

### Response

<ResponseField name="id" type="string">
  Stable identifier for the endpoint. Use this in every per-endpoint path parameter.
</ResponseField>

<ResponseField name="slug" type="string">
  The endpoint's routing slug.
</ResponseField>

<ResponseField name="targets" type="object[]">
  The endpoint's configured targets. Each entry echoes `provider` plus the applicable fields: `model_id` and, for non-production environments, `environment_name` for Baseten targets; or `secret_id` and `target_model` for external providers.
</ResponseField>

<ResponseField name="created_at" type="string">
  RFC 3339 UTC timestamp of creation.
</ResponseField>

<ResponseField name="updated_at" type="string">
  RFC 3339 UTC timestamp of the last update.
</ResponseField>

### Errors

| Status            | Meaning                                                                                                                                                                                                |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `400 Bad Request` | Invalid payload, slug prefix your organization doesn't own, duplicate slug, unknown environment, invalid provider-specific target fields, or a `targets` list that's empty or has more than one entry. |
| `403 Forbidden`   | Workspace isn't onboarded to Frontier Gateway, or the caller doesn't have management scope.                                                                                                            |

<RequestExample>
  ```bash curl theme={"system"}
  curl --request POST \
    --url https://api.baseten.co/v1/gateway/endpoints \
    --header "Authorization: Api-Key $BASETEN_API_KEY" \
    --header "Content-Type: application/json" \
    --data '{
      "slug": "my-org/glm-5.2",
      "targets": [
        {
          "provider": "BASETEN",
          "model_id": "3kZ9xqd",
          "environment_name": "staging"
        }
      ]
    }'
  ```
</RequestExample>

<ResponseExample>
  ```json 200 theme={"system"}
  {
    "id": "abc123hash",
    "slug": "my-org/glm-5.2",
    "targets": [
      {
        "provider": "BASETEN",
        "model_id": "3kZ9xqd",
        "environment_name": "staging"
      }
    ],
    "created_at": "2026-06-17T12:00:00Z",
    "updated_at": "2026-06-17T12:00:00Z"
  }
  ```
</ResponseExample>
