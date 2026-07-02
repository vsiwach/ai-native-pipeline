# Get an endpoint
Source: https://docs.baseten.co/reference/gateway/endpoints/get-an-endpoint

GET https://api.baseten.co/v1/gateway/endpoints/{endpoint_id}
Retrieve a single Frontier Gateway endpoint by its ID.

Retrieve a single endpoint by its `id`, including its slug and configured targets.

### Authentication

<ParamField type="string">
  Workspace API key with management scope, passed as `Authorization: Api-Key $BASETEN_API_KEY` (or `Bearer`; both are accepted).
</ParamField>

### Path parameters

<ParamField type="string">
  Identifier of the endpoint, returned as `id` by [Create an endpoint](/reference/gateway/endpoints/create-an-endpoint).
</ParamField>

### Response

The endpoint, with the same shape as the [Create an endpoint](/reference/gateway/endpoints/create-an-endpoint#response) response: `id`, `slug`, `targets`, `created_at`, and `updated_at`.

### Errors

| Status          | Meaning                                                                                       |
| --------------- | --------------------------------------------------------------------------------------------- |
| `403 Forbidden` | The endpoint exists but isn't in your workspace, or the caller doesn't have management scope. |
| `404 Not Found` | No endpoint with this `id` in your workspace.                                                 |

<RequestExample>
  ```bash curl theme={"system"}
  curl --request GET \
    --url https://api.baseten.co/v1/gateway/endpoints/abc123hash \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
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
