# Update a group
Source: https://docs.baseten.co/reference/gateway/groups/update-a-group

PATCH https://api.baseten.co/v1/gateway/groups/{group_id}
Update a Frontier Gateway group's display name or model configuration. Hierarchy and enforcement mode are immutable.

Update a group's mutable fields. You can change `metadata.name` and the `models` configuration; the `hierarchy` block (parent and enforcement mode) is immutable after creation. At least one field must be provided.

The `models` list, when provided, replaces the group's full model set with **set semantics**: slugs absent from the new list are removed, and slugs that are new to the group are added.

### Authentication

<ParamField type="string">
  Workspace API key with management scope, passed as `Authorization: Api-Key $BASETEN_API_KEY` (or `Bearer`; both are accepted).
</ParamField>

### Path parameters

<ParamField type="string">
  Internal Baseten ID of the group to update.
</ParamField>

### Body

At least one of `metadata` or `models` must be provided.

<ParamField type="object">
  Mutable group metadata.

  * **`name`** (`string`, optional, max length 255): Display name for the group.

  `metadata.external_entity_id` cannot be changed. To re-key a group, delete it and create a fresh one.
</ParamField>

<ParamField type="object[]">
  Replacement model configuration. Same shape as the request body of [Create a group](/reference/gateway/groups/create-a-group). Replaces the existing list with set semantics.

  Passing an empty list (`"models": []`) clears every model from the group, which also removes model access from every key under it. Omit the field entirely to leave the model set unchanged.
</ParamField>

### Response

Same shape returned by [Create a group](/reference/gateway/groups/create-a-group#response), reflecting the post-update state. `effective_models` is recomputed for this group and propagated to descendants.

### Errors

| Status            | Meaning                                                                                                                                                                                                                                                                                                                |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `400 Bad Request` | Empty body, invalid limit shape, or (in a cascading hierarchy) a change that would put this group above an ancestor or below an existing descendant. Lower descendants before lowering the parent, and raise ancestors before raising descendants. See [Cascading mode](/frontier-gateway/rate-limits#cascading-mode). |
| `403 Forbidden`   | The group exists but isn't in your workspace, or the caller doesn't have management scope.                                                                                                                                                                                                                             |
| `404 Not Found`   | No group with this `id` in your workspace, or it has been deleted.                                                                                                                                                                                                                                                     |

<RequestExample>
  ```bash curl theme={"system"}
  curl --request PATCH \
    --url https://api.baseten.co/v1/gateway/groups/abc123hash \
    --header "Authorization: Api-Key $BASETEN_API_KEY" \
    --header "Content-Type: application/json" \
    --data '{
      "models": [
        {
          "slug": "your-org/your-model",
          "rate_limits": [
            { "type": "TOKEN", "unit": "MINUTE", "threshold": 1500000 }
          ]
        }
      ]
    }'
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
          { "type": "TOKEN", "unit": "MINUTE", "threshold": 1500000 }
        ],
        "usage_limits": []
      }
    ],
    "effective_models": [
      {
        "slug": "your-org/your-model",
        "rate_limits": [
          { "type": "TOKEN", "unit": "MINUTE", "threshold": 1500000, "source_group": "abc123hash" }
        ],
        "usage_limits": []
      }
    ],
    "hierarchy": { "limit_enforcement": "INDEPENDENT", "parent_group_id": null },
    "created_at": "2026-05-13T12:00:00Z"
  }
  ```
</ResponseExample>
