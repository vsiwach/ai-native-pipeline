# Update an endpoint
Source: https://docs.baseten.co/reference/gateway/endpoints/replace-endpoint-targets

PATCH https://api.baseten.co/v1/gateway/endpoints/{endpoint_id}
Update a Frontier Gateway endpoint's slug or targets.

Update an endpoint's mutable fields. Send the fields you want to change. If you include `targets`, the value replaces the endpoint's full target list. If you include `slug`, the endpoint is renamed.

### Authentication

<ParamField type="string">
  Workspace API key with management scope, passed as `Authorization: Api-Key $BASETEN_API_KEY` (or `Bearer`; both are accepted).
</ParamField>

### Path parameters

<ParamField type="string">
  Identifier of the endpoint, returned as `id` by [Create an endpoint](/reference/gateway/endpoints/create-an-endpoint).
</ParamField>

### Body

Send only the fields you want to change.

<ParamField type="string">
  New globally-unique routing slug, formatted `{org_prefix}/{name}`. The `org_prefix` must be a prefix your organization owns.
</ParamField>

<ParamField type="object[]">
  The endpoint's complete target list after the call. Exactly one target is supported at this time: send a list of length one. Sending an empty list or more than one target returns `400`.

  Each entry takes:

  * **`provider`** (`string`, required): Upstream provider for the target. One of `BASETEN`, `ANTHROPIC`, or `OPENAI`.
  * **`model_id`** (`string`): The Baseten model the slug routes to. Use for `BASETEN` targets.
  * **`environment_name`** (`string`): Baseten model environment to route to. Only valid for `BASETEN` targets. Omit it, or pass `production`, to target production.
  * **`secret_id`** (`string`): Baseten secret holding the provider credential. Required for external providers (`ANTHROPIC`, `OPENAI`).
  * **`target_model`** (`string`): Upstream model name to send. Required for external providers; optional for `BASETEN`.
</ParamField>

### Response

The updated endpoint, with the same shape as the [Create an endpoint](/reference/gateway/endpoints/create-an-endpoint#response) response: `id`, `slug`, `targets`, `created_at`, and `updated_at`.

### Errors

| Status            | Meaning                                                                                                                                     |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `400 Bad Request` | Invalid payload, unknown environment, invalid provider-specific target fields, or a `targets` list that's empty or has more than one entry. |
| `403 Forbidden`   | The endpoint exists but isn't in your workspace, or the caller doesn't have management scope.                                               |
| `404 Not Found`   | No endpoint with this `id` in your workspace.                                                                                               |

<RequestExample>
  ```bash curl theme={"system"}
  curl --request PATCH \
    --url https://api.baseten.co/v1/gateway/endpoints/abc123hash \
    --header "Authorization: Api-Key $BASETEN_API_KEY" \
    --header "Content-Type: application/json" \
    --data '{
      "targets": [
        {
          "provider": "BASETEN",
          "model_id": "7mP2wqe",
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
        "model_id": "7mP2wqe",
        "environment_name": "staging"
      }
    ],
    "created_at": "2026-06-17T12:00:00Z",
    "updated_at": "2026-06-17T13:30:00Z"
  }
  ```
</ResponseExample>
