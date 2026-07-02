# Get group usage
Source: https://docs.baseten.co/reference/gateway/groups/get-group-usage

GET https://api.baseten.co/v1/gateway/groups/{group_id}/usage
Read current-window consumption against the usage limits configured on a Frontier Gateway group.

Return current-window consumption for a single group, broken down by model. The response only includes models that have `usage_limits` configured. Rate limits are not surfaced here. Use this endpoint to power per-customer dashboards or to check remaining quota before issuing a workload.

This endpoint is the Frontier Gateway equivalent of the legacy per-API-key usage lookup: usage now hangs off the group, and every API key under the group reports against the same counters.

### Authentication

<ParamField type="string">
  Workspace API key with management scope, passed as `Authorization: Api-Key $BASETEN_API_KEY` (or `Bearer`; both are accepted).
</ParamField>

### Path parameters

<ParamField type="string">
  Internal Baseten ID of the group. Returned as `id` from [Create a group](/reference/gateway/groups/create-a-group) and from [List groups](/reference/gateway/groups/list-groups).
</ParamField>

### Response

<ResponseField name="customer_id" type="string">
  The group's external identifier, the value you passed as `metadata.external_entity_id` when creating the group.
</ResponseField>

<ResponseField name="usage" type="object">
  Per-model usage entries, keyed by the model slug. Only models that have `usage_limits` configured on the group's effective configuration appear here; a group with no configured usage limits returns an empty object.

  Each value is an array of usage entries, one per configured `(type, unit)` pair:

  * **`type`** (`string`): `TOKEN` or `REQUEST`.
  * **`unit`** (`string`): Window size for the limit. `DAY` is the only supported value.
  * **`threshold`** (`integer`): Configured quota for the window.
  * **`current_usage`** (`integer` or `null`): Total consumption in the current window. `null` until the first request lands.
  * **`reset_at`** (`string` or `null`): UTC timestamp when the current window resets. `null` until the first request lands.
</ResponseField>

### Errors

| Status          | Meaning                                                                                    |
| --------------- | ------------------------------------------------------------------------------------------ |
| `403 Forbidden` | The group exists but isn't in your workspace, or the caller doesn't have management scope. |
| `404 Not Found` | No group with this `id` in your workspace, or it has been deleted.                         |

<RequestExample>
  ```bash curl theme={"system"}
  curl --request GET \
    --url https://api.baseten.co/v1/gateway/groups/abc123hash/usage \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```
</RequestExample>

<ResponseExample>
  ```json 200 theme={"system"}
  {
    "customer_id": "cust_42",
    "usage": {
      "your-org/your-model": [
        {
          "type": "TOKEN",
          "unit": "DAY",
          "threshold": 10000000,
          "current_usage": 4231899,
          "reset_at": "2026-05-21T00:00:00Z"
        }
      ]
    }
  }
  ```
</ResponseExample>
