# Get an API key
Source: https://docs.baseten.co/reference/gateway/api-keys/get-an-api-key

GET https://api.baseten.co/v1/gateway/groups/{group_id}/api_keys/{api_key_prefix}
Fetch metadata for one federated API key by its prefix. The plaintext key is never returned after creation.

Fetch one federated API key by its `prefix`. Only metadata is returned; the plaintext key is shown exactly once at creation and is unrecoverable afterward. To inspect the model access and limits the key resolves to, fetch its [group](/reference/gateway/groups/get-a-group) and read the `effective_models` block.

### Authentication

<ParamField type="string">
  Workspace API key with management scope, passed as `Authorization: Api-Key $BASETEN_API_KEY` (or `Bearer`; both are accepted).
</ParamField>

### Path parameters

<ParamField type="string">
  Internal Baseten ID of the owning group.
</ParamField>

<ParamField type="string">
  The key's prefix (the substring before the `.` in the full key string). Returned as `prefix` from [Create an API key](/reference/gateway/api-keys/create-an-api-key) and from [List API keys for a group](/reference/gateway/api-keys/list-api-keys-for-a-group).
</ParamField>

### Response

<ResponseField name="prefix" type="string">
  The key's prefix.
</ResponseField>

<ResponseField name="name" type="string">
  Display name set when the key was minted. `null` if no name was provided.
</ResponseField>

### Errors

| Status          | Meaning                                                                                           |
| --------------- | ------------------------------------------------------------------------------------------------- |
| `403 Forbidden` | The group or key exists but isn't in your workspace, or the caller doesn't have management scope. |
| `404 Not Found` | No group or key with these identifiers in your workspace, or the key has been revoked.            |

<RequestExample>
  ```bash curl theme={"system"}
  curl --request GET \
    --url https://api.baseten.co/v1/gateway/groups/abc123hash/api_keys/sky_sCqhBwEy4kPd \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```
</RequestExample>

<ResponseExample>
  ```json 200 theme={"system"}
  {
    "prefix": "sky_sCqhBwEy4kPd",
    "name": "prod-key-1"
  }
  ```
</ResponseExample>
