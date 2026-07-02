# Create a group
Source: https://docs.baseten.co/reference/gateway/groups/create-a-group

POST https://api.baseten.co/v1/gateway/groups
Create a Frontier Gateway group with its model set, per-model limits, and a place in the hierarchy.

Create a Frontier Gateway group. Groups own the external identifier, the model set, the rate and usage limits, and the inheritance mode. API keys are minted under groups in a separate call. For the conceptual walkthrough, see [Manage groups and API keys](/frontier-gateway/api-keys).

### Authentication

<ParamField type="string">
  Workspace API key with management scope, passed as `Authorization: Api-Key $BASETEN_API_KEY` (or `Bearer`; both are accepted).
</ParamField>

### Body

<ParamField type="object">
  Group identity and display metadata.

  * **`name`** (`string`, optional, max length 255): Display name for the group.
  * **`external_entity_id`** (`string`, required, length 1-255): Stable identifier you choose. Unique within your workspace. Surfaces as `externalEntityId` on every [billing webhook](/frontier-gateway/billing-webhooks) event for keys under this group.
</ParamField>

<ParamField type="object[]">
  Per-model rate and usage limit configuration. Must be non-empty.

  Each entry takes:

  * **`slug`** (`string`, required): Model slug, formatted `your-org/your-model`.
  * **`rate_limits`** (`object[]`, optional): Short-window limits. Each entry: `type` (`TOKEN`, `REQUEST`), `unit` (`SECOND`, `MINUTE`), `threshold` (integer `>= 1`). At most one entry per `type` per slug.
  * **`usage_limits`** (`object[]`, optional): Daily-window limits. Each entry: `type` (`TOKEN`, `REQUEST`), `unit` (`DAY`), `threshold` (integer `>= 1`). At most one entry per (`type`, `unit`) per slug.

  For the full limit-shape reference, see [Rate and usage limits](/frontier-gateway/rate-limits).
</ParamField>

<ParamField type="object">
  Parent linkage and limit enforcement mode. Both fields are immutable after creation.

  * **`limit_enforcement`** (`string`, required): One of `INDEPENDENT` or `CASCADING`. Must match the parent's mode if `parent_group_id` is set. For semantics, see [Inheritance modes](/frontier-gateway/rate-limits#inheritance-modes).
  * **`parent_group_id`** (`string` or `null`, required): The `id` of the parent group, or `null` for a root group. Hierarchies are capped at five levels deep.
</ParamField>

### Response

<ResponseField name="id" type="string">
  Internal Baseten ID for the new group. Use this in every per-group path parameter.
</ResponseField>

<ResponseField name="metadata" type="object">
  Echoes the request `metadata`.
</ResponseField>

<ResponseField name="models" type="object[]">
  Echoes the request `models` after persistence. Same shape as the request body.
</ResponseField>

<ResponseField name="effective_models" type="object[]">
  The per-model limits the runtime enforces after walking the hierarchy. Same shape as `models`, with one extra field on every `rate_limits` and `usage_limits` entry: `source_group` (`string`), the `id` of the group the limit is anchored to (this group or an ancestor).
</ResponseField>

<ResponseField name="hierarchy" type="object">
  Echoes the request `hierarchy`. `parent_group_id` is `null` for root groups.
</ResponseField>

<ResponseField name="created_at" type="string">
  RFC 3339 UTC timestamp of creation.
</ResponseField>

### Errors

| Status            | Meaning                                                                                                                                                                                    |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `400 Bad Request` | Invalid payload, duplicate `external_entity_id`, mixed enforcement modes in the same hierarchy, hierarchy exceeds five levels, or a cascading child whose threshold exceeds an ancestor's. |
| `403 Forbidden`   | Workspace isn't onboarded to Frontier Gateway, or the caller doesn't have management scope.                                                                                                |
| `404 Not Found`   | `hierarchy.parent_group_id` references a group that doesn't exist or isn't visible to your workspace.                                                                                      |

<RequestExample>
  ```bash curl theme={"system"}
  curl --request POST \
    --url https://api.baseten.co/v1/gateway/groups \
    --header "Authorization: Api-Key $BASETEN_API_KEY" \
    --header "Content-Type: application/json" \
    --data '{
      "metadata": {
        "name": "Acme prod",
        "external_entity_id": "cust_42"
      },
      "models": [
        {
          "slug": "your-org/your-model",
          "rate_limits": [
            { "type": "TOKEN", "unit": "MINUTE", "threshold": 1000000 },
            { "type": "REQUEST", "unit": "MINUTE", "threshold": 100 }
          ],
          "usage_limits": [
            { "type": "TOKEN", "unit": "DAY", "threshold": 10000000 }
          ]
        }
      ],
      "hierarchy": {
        "limit_enforcement": "INDEPENDENT",
        "parent_group_id": null
      }
    }'
  ```
</RequestExample>

<ResponseExample>
  ```json 200 theme={"system"}
  {
    "id": "abc123hash",
    "metadata": {
      "name": "Acme prod",
      "external_entity_id": "cust_42"
    },
    "models": [
      {
        "slug": "your-org/your-model",
        "rate_limits": [
          { "type": "TOKEN", "unit": "MINUTE", "threshold": 1000000 },
          { "type": "REQUEST", "unit": "MINUTE", "threshold": 100 }
        ],
        "usage_limits": [
          { "type": "TOKEN", "unit": "DAY", "threshold": 10000000 }
        ]
      }
    ],
    "effective_models": [
      {
        "slug": "your-org/your-model",
        "rate_limits": [
          { "type": "TOKEN", "unit": "MINUTE", "threshold": 1000000, "source_group": "abc123hash" },
          { "type": "REQUEST", "unit": "MINUTE", "threshold": 100, "source_group": "abc123hash" }
        ],
        "usage_limits": [
          { "type": "TOKEN", "unit": "DAY", "threshold": 10000000, "source_group": "abc123hash" }
        ]
      }
    ],
    "hierarchy": {
      "limit_enforcement": "INDEPENDENT",
      "parent_group_id": null
    },
    "created_at": "2026-05-13T12:00:00Z"
  }
  ```
</ResponseExample>
