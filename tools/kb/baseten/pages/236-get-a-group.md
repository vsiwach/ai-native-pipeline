# Get a group
Source: https://docs.baseten.co/reference/gateway/groups/get-a-group

GET https://api.baseten.co/v1/gateway/groups/{group_id}
Fetch a single Frontier Gateway group by its internal id, including its effective limits after inheritance.

Fetch one group by its internal `id`. The response includes the group's own `models` configuration plus the post-inheritance `effective_models` block. To look up a group by your external identifier instead, use [List groups](/reference/gateway/groups/list-groups) with `?external_entity_id=`.

### Authentication

<ParamField type="string">
  Workspace API key with management scope, passed as `Authorization: Api-Key $BASETEN_API_KEY` (or `Bearer`; both are accepted).
</ParamField>

### Path parameters

<ParamField type="string">
  Internal Baseten ID of the group. Returned as `id` from [Create a group](/reference/gateway/groups/create-a-group) and from [List groups](/reference/gateway/groups/list-groups).
</ParamField>

### Response

Same shape returned by [Create a group](/reference/gateway/groups/create-a-group#response): `id`, `metadata`, `models`, `effective_models`, `hierarchy`, `created_at`.

### Errors

| Status          | Meaning                                                                                    |
| --------------- | ------------------------------------------------------------------------------------------ |
| `403 Forbidden` | The group exists but isn't in your workspace, or the caller doesn't have management scope. |
| `404 Not Found` | No group with this `id` in your workspace, or it has been deleted.                         |

<RequestExample>
  ```bash curl theme={"system"}
  curl --request GET \
    --url https://api.baseten.co/v1/gateway/groups/abc123hash \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```
</RequestExample>

<ResponseExample>
  ```json 200 theme={"system"}
  {
    "id": "abc123hash",
    "metadata": { "name": "Acme prod", "external_entity_id": "cust_42" },
    "models": [
      {
        "slug": "your-org/your-model",
        "rate_limits": [
          { "type": "TOKEN", "unit": "MINUTE", "threshold": 1000000 }
        ],
        "usage_limits": []
      }
    ],
    "effective_models": [
      {
        "slug": "your-org/your-model",
        "rate_limits": [
          { "type": "TOKEN", "unit": "MINUTE", "threshold": 1000000, "source_group": "abc123hash" }
        ],
        "usage_limits": []
      }
    ],
    "hierarchy": { "limit_enforcement": "INDEPENDENT", "parent_group_id": null },
    "created_at": "2026-05-13T12:00:00Z"
  }
  ```
</ResponseExample>
