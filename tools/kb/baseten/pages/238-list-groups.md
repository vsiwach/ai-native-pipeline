# List groups
Source: https://docs.baseten.co/reference/gateway/groups/list-groups

GET https://api.baseten.co/v1/gateway/groups
List Frontier Gateway groups in your workspace. Cursor-paginated, with optional lookup by external identifier.

List groups visible to your workspace, cursor-paginated. Pass `external_entity_id` to look up a single group by its external identifier.

### Authentication

<ParamField type="string">
  Workspace API key with management scope, passed as `Authorization: Api-Key $BASETEN_API_KEY` (or `Bearer`; both are accepted).
</ParamField>

### Query parameters

<ParamField type="string">
  Filter results to groups whose `metadata.external_entity_id` matches this value exactly. Because `external_entity_id` is unique per workspace, the response contains at most one item. Combinable with `limit` and `cursor`.
</ParamField>

<ParamField type="integer">
  Page size. Default 100, maximum 1000.
</ParamField>

<ParamField type="string">
  Pagination cursor from the previous response's `pagination.cursor`. Omit on the first call.
</ParamField>

### Response

<ResponseField name="items" type="object[]">
  Group objects. Each item has the same shape returned by [Create a group](/reference/gateway/groups/create-a-group#response): `id`, `metadata`, `models`, `effective_models`, `hierarchy`, `created_at`.
</ResponseField>

<ResponseField name="pagination" type="object">
  * **`has_more`** (`boolean`): `true` when more pages exist.
  * **`cursor`** (`string` or `null`): Cursor for the next page. `null` on the last page.
</ResponseField>

### Errors

| Status          | Meaning                                                                               |
| --------------- | ------------------------------------------------------------------------------------- |
| `403 Forbidden` | Workspace isn't onboarded to Frontier Gateway, or the caller doesn't have view scope. |

<RequestExample>
  ```bash curl theme={"system"}
  curl --request GET \
    --url https://api.baseten.co/v1/gateway/groups \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```

  ```bash by external_entity_id theme={"system"}
  curl --request GET \
    --url "https://api.baseten.co/v1/gateway/groups?external_entity_id=cust_42" \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```

  ```bash next page theme={"system"}
  curl --request GET \
    --url "https://api.baseten.co/v1/gateway/groups?cursor=aVd2Yk54T2d2V0dFWE13R1l4R2k5UVE=" \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```
</RequestExample>

<ResponseExample>
  ```json 200 theme={"system"}
  {
    "items": [
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
    ],
    "pagination": {
      "has_more": true,
      "cursor": "aVd2Yk54T2d2V0dFWE13R1l4R2k5UVE="
    }
  }
  ```
</ResponseExample>
