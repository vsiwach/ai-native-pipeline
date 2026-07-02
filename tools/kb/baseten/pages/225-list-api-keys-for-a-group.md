# List API keys for a group
Source: https://docs.baseten.co/reference/gateway/api-keys/list-api-keys-for-a-group

GET https://api.baseten.co/v1/gateway/groups/{group_id}/api_keys
List the federated API keys minted under a Frontier Gateway group. Cursor-paginated.

List the federated API keys minted under a group. Results are cursor-paginated. Per-key responses carry only the `prefix` and `name`; to inspect the model access and limits a key resolves to, fetch its [group](/reference/gateway/groups/get-a-group) and read the `effective_models` block.

### Authentication

<ParamField type="string">
  Workspace API key with management scope, passed as `Authorization: Api-Key $BASETEN_API_KEY` (or `Bearer`; both are accepted).
</ParamField>

### Path parameters

<ParamField type="string">
  Internal Baseten ID of the group whose keys you want to list.
</ParamField>

### Query parameters

<ParamField type="integer">
  Page size. Default 100, maximum 1000.
</ParamField>

<ParamField type="string">
  Pagination cursor from the previous response's `pagination.cursor`. Omit on the first call.
</ParamField>

### Response

<ResponseField name="items" type="object[]">
  Key objects. Each item:

  * **`prefix`** (`string`): The key's prefix.
  * **`name`** (`string` or `null`): Display name set when the key was minted.
</ResponseField>

<ResponseField name="pagination" type="object">
  * **`has_more`** (`boolean`): `true` when more pages exist.
  * **`cursor`** (`string` or `null`): Cursor for the next page. `null` on the last page.
</ResponseField>

### Errors

| Status          | Meaning                                                                                    |
| --------------- | ------------------------------------------------------------------------------------------ |
| `403 Forbidden` | The group exists but isn't in your workspace, or the caller doesn't have management scope. |
| `404 Not Found` | No group with this `id` in your workspace, or it has been deleted.                         |

<RequestExample>
  ```bash curl theme={"system"}
  curl --request GET \
    --url https://api.baseten.co/v1/gateway/groups/abc123hash/api_keys \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```
</RequestExample>

<ResponseExample>
  ```json 200 theme={"system"}
  {
    "items": [
      {
        "prefix": "sky_sCqhBwEy4kPd",
        "name": "prod-key-1"
      }
    ],
    "pagination": {
      "has_more": false,
      "cursor": null
    }
  }
  ```
</ResponseExample>
