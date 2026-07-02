# Manage groups and API keys
Source: https://docs.baseten.co/frontier-gateway/api-keys

Walk the full lifecycle: create groups, build a hierarchy, mint and revoke API keys, and delete groups when a customer churns.

In Frontier Gateway, every API key belongs to a **group**: the resource that owns one billable entity's external identifier, model set, rate and usage limits, and place in your organizational hierarchy. You manage groups and their keys yourself through the [REST API](/reference/gateway/overview). This page walks the full lifecycle: creating a group, building a hierarchy, minting a key, listing and revoking keys, and deleting a group.

## Concepts

A **group** is one node in your hierarchy. The group owns:

* A **`metadata.external_entity_id`**: a stable identifier you choose, unique within your workspace. Use it to map the group back to your own system. The same value is included as `externalEntityId` on every [billing webhook](/frontier-gateway/billing-webhooks) event for the group's keys.
* A **`metadata.name`**: an optional human-readable display name.
* A **model set** (`models[]`): the [endpoint](/frontier-gateway/endpoints) slugs the group is allowed to call, each with optional rate and usage limits.
* A **`hierarchy`** block: a `limit_enforcement` mode (one of `INDEPENDENT` or `CASCADING`) and an optional `parent_group_id`. Both fields are **immutable** after creation.

A **federated API key** is a credential bound to one group. Keys are minted under the group; rotating credentials for a customer means revoking and reissuing the key without touching the group. Each key has a **prefix** (the substring before the `.` in the full key string) used as the path parameter in every per-key URL. The plaintext secret after the `.` is shown once at creation and is never retrievable; lose it and you must revoke and reissue. A key's model access and limits are derived entirely from its group's effective config; keys don't carry per-key overrides.

To see how limits compose across a hierarchy, see [Rate and usage limits](/frontier-gateway/rate-limits).

## Create a group

Create a group to represent one billable entity, such as a customer, plan, or project, along with the model set and limits its keys inherit. The body specifies the group's metadata, its complete model configuration, and a `hierarchy` block declaring the inheritance mode and an optional parent. The `models` list defines the group's complete model set with **set semantics**. Slugs added to the list are added to the group, and slugs absent from the list on a later update are removed (cascading to existing keys' access). The response is the new group; save the `id`, which is the path parameter for every per-group operation that follows.

<CodeGroup>
  ```bash Request theme={"system"}
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

  ```json Output theme={"system"}
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
</CodeGroup>

The `models` list must be non-empty on create. To clear models from an existing group later, send `"models": []` on `PATCH`; to remove the group entirely, see [Delete a group](#delete-a-group). For the limit-shape reference, see [Rate and usage limits](/frontier-gateway/rate-limits).

For more information, see [`POST /v1/gateway/groups`](/reference/gateway/groups/create-a-group).

## Build a hierarchy

Build a hierarchy to nest groups (for example, a customer with per-team subgroups) so limits flow from parents down to children. To nest a group under an existing one, pass the parent's `id` as `hierarchy.parent_group_id`. The child's `limit_enforcement` mode must match the root of its subtree. Pick the mode when you create the root, then every descendant uses the same mode. The child group's response includes the same `models` it was configured with, plus an `effective_models` block showing the limits the runtime enforces after walking up the tree.

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request POST \
    --url https://api.baseten.co/v1/gateway/groups \
    --header "Authorization: Api-Key $BASETEN_API_KEY" \
    --header "Content-Type: application/json" \
    --data '{
      "metadata": {
        "name": "Acme prod / engineering",
        "external_entity_id": "cust_42_engineering"
      },
      "models": [
        {
          "slug": "your-org/your-model",
          "rate_limits": [
            { "type": "TOKEN", "unit": "MINUTE", "threshold": 700000 }
          ]
        }
      ],
      "hierarchy": {
        "limit_enforcement": "INDEPENDENT",
        "parent_group_id": "abc123hash"
      }
    }'
  ```

  ```json Output theme={"system"}
  {
    "id": "def456hash",
    "metadata": {
      "name": "Acme prod / engineering",
      "external_entity_id": "cust_42_engineering"
    },
    "models": [
      {
        "slug": "your-org/your-model",
        "rate_limits": [
          { "type": "TOKEN", "unit": "MINUTE", "threshold": 700000 }
        ],
        "usage_limits": []
      }
    ],
    "effective_models": [
      {
        "slug": "your-org/your-model",
        "rate_limits": [
          { "type": "TOKEN", "unit": "MINUTE", "threshold": 700000, "source_group": "def456hash" }
        ],
        "usage_limits": []
      }
    ],
    "hierarchy": {
      "limit_enforcement": "INDEPENDENT",
      "parent_group_id": "abc123hash"
    },
    "created_at": "2026-05-13T12:05:00Z"
  }
  ```
</CodeGroup>

Each limit in `effective_models` carries a `source_group` field pointing to the ancestor (or self) that the limit was anchored to. For a worked example, see [Effective limits and inheritance](/frontier-gateway/rate-limits#effective-limits-and-inheritance).

For more information, see [`POST /v1/gateway/groups`](/reference/gateway/groups/create-a-group).

## List groups

List groups to see every group you've provisioned, or to look up a specific customer by external identifier. Results are cursor-paginated. Pass `?external_entity_id=` to look up a single group by its external identifier. The response includes a `pagination` block with `has_more` and a `cursor` you pass back to fetch the next page.

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request GET \
    --url https://api.baseten.co/v1/gateway/groups \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```

  ```json Output theme={"system"}
  {
    "items": [
      {
        "id": "abc123hash",
        "metadata": { "name": "Acme prod", "external_entity_id": "cust_42" },
        "models": [ /* ... */ ],
        "effective_models": [ /* ... */ ],
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
</CodeGroup>

To fetch the next page, pass the previous response's cursor. You've drained the result set when the response has `"has_more": false` and `"cursor": null`.

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request GET \
    --url "https://api.baseten.co/v1/gateway/groups?cursor=aVd2Yk54T2d2V0dFWE13R1l4R2k5UVE=" \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```

  ```json Output theme={"system"}
  {
    "items": [
      {
        "id": "def456hash",
        "metadata": { "name": "Acme prod / engineering", "external_entity_id": "cust_42_engineering" },
        "models": [ /* ... */ ],
        "effective_models": [ /* ... */ ],
        "hierarchy": { "limit_enforcement": "INDEPENDENT", "parent_group_id": "abc123hash" },
        "created_at": "2026-05-13T12:05:00Z"
      }
    ],
    "pagination": {
      "has_more": false,
      "cursor": null
    }
  }
  ```
</CodeGroup>

For more information, see [`GET /v1/gateway/groups`](/reference/gateway/groups/list-groups).

## Update a group

Update a group to change its display name or adjust the model set and limits its keys inherit. You can change `metadata.name` and the `models` configuration; the `hierarchy` block (parent and enforcement mode) is immutable after creation. At least one of `metadata.name` or `models` must be provided.

Replacing `models` follows the same set semantics as create: every slug currently on the group but absent from the new list is removed (cascading to existing keys' access), and new slugs are added.

If the group sits in a cascading hierarchy, the new `models` block is validated against both the group's ancestors and its descendants. A `PATCH` that would raise the group above an ancestor's threshold, or lower the group below a descendant's threshold, is rejected with `400 Bad Request: "Child group exceeds parent group limit."`. See [Cascading mode](/frontier-gateway/rate-limits#cascading-mode) for the full ordering rules.

The response is the updated group, with refreshed `effective_models` reflecting the new limits and any downstream inheritance.

<CodeGroup>
  ```bash Request theme={"system"}
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

  ```json Output theme={"system"}
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
</CodeGroup>

For more information, see [`PATCH /v1/gateway/groups/{group_id}`](/reference/gateway/groups/update-a-group).

## Mint an API key

Mint an API key to give a customer a credential bound to the group, inheriting its model set and limits. The path parameter is the group's internal `id` (not its `external_entity_id`). The body has a single optional `name` field: a display label for the key. Keys inherit the group's effective model set and limits; you can't restrict a key to a subset of the group's slugs or attach per-key limits.

The response contains the plaintext key, returned exactly once.

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request POST \
    --url https://api.baseten.co/v1/gateway/groups/abc123hash/api_keys \
    --header "Authorization: Api-Key $BASETEN_API_KEY" \
    --header "Content-Type: application/json" \
    --data '{
      "name": "prod-key-1"
    }'
  ```

  ```json Output theme={"system"}
  {
    "api_key": "sky_sCqhBwEy4kPd.<api-key-secret>",
    "prefix": "sky_sCqhBwEy4kPd",
    "name": "prod-key-1"
  }
  ```
</CodeGroup>

<Warning>
  This is the only time the key is returned in plaintext. Save it now: Baseten doesn't store the secret portion and can't show it to you again. If you lose it, revoke the key and mint a new one.
</Warning>

To rotate a customer's credentials without changing their access or limits, mint a new key under the same group, hand the new key to the customer, then revoke the old one once they've cut over.

For more information, see [`POST /v1/gateway/groups/{group_id}/api_keys`](/reference/gateway/api-keys/create-an-api-key).

## Register an existing API key

Register an existing API key when you already mint keys on your own platform and want their traffic to flow through Frontier Gateway without forcing your downstream customers to rotate. The registered key inherits the group's effective model set and limits, exactly like a key produced by [Mint an API key](#mint-an-api-key).

Supply the plaintext key in the `key` field. Baseten validates that the value is between 32 and 128 characters and has at least 3.0 bits of Shannon entropy per character; any cryptographically secure random key clears the entropy check.

Because this endpoint accepts a key you control, Baseten requires a signature on each request. Sign the exact bytes of the body with your workspace's Ed25519 private key, base64-encode the result, and pass it in the `X-Baseten-Signature` header. Register your public key with Baseten first; until a key is on file, every call returns `400 Bad Request`. See [Register an API key](/reference/gateway/api-keys/register-an-api-key#request-signing) for keypair generation and the full signing steps.

The response confirms the registration. Baseten doesn't echo the key back, so save it on your side before calling.

<CodeGroup>
  ```bash Request theme={"system"}
  BODY='{"name":"acme-prod-key-1","key":"<your-securely-generated-api-key>"}'
  SIGNATURE=$(printf '%s' "$BODY" | openssl pkeyutl -sign -inkey priv.pem -rawin | openssl base64 -A)

  curl --request POST \
    --url https://api.baseten.co/v1/gateway/groups/abc123hash/api_keys/register \
    --header "Authorization: Api-Key $BASETEN_API_KEY" \
    --header "Content-Type: application/json" \
    --header "X-Baseten-Signature: $SIGNATURE" \
    --data "$BODY"
  ```

  ```json Output theme={"system"}
  {
    "ok": true
  }
  ```
</CodeGroup>

The first 16 characters of the supplied key become the stored `prefix` and must be unique within your workspace. Use that prefix as the path parameter when you fetch or revoke the key later. For the full constraint list and error semantics, see [Register an API key](/reference/gateway/api-keys/register-an-api-key).

<Warning>
  Baseten stores only the hashed key. Once registered, the plaintext value is unrecoverable from our side. Handle it through your own secure channel before calling this endpoint.
</Warning>

For more information, see [`POST /v1/gateway/groups/{group_id}/api_keys/register`](/reference/gateway/api-keys/register-an-api-key).

## List a group's keys

List a group's keys to see which credentials are active for a customer. Results are cursor-paginated with the same shape as the [group list](#list-groups).

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request GET \
    --url https://api.baseten.co/v1/gateway/groups/abc123hash/api_keys \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```

  ```json Output theme={"system"}
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
</CodeGroup>

Per-key responses carry only the `prefix` and `name`. To inspect the model access and limits the key resolves to, fetch its [group](#list-groups) and read the `effective_models` block.

To fetch a single key by prefix, use `GET /v1/gateway/groups/{group_id}/api_keys/{api_key_prefix}`:

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request GET \
    --url https://api.baseten.co/v1/gateway/groups/abc123hash/api_keys/sky_sCqhBwEy4kPd \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```

  ```json Output theme={"system"}
  {
    "prefix": "sky_sCqhBwEy4kPd",
    "name": "prod-key-1"
  }
  ```
</CodeGroup>

For more information, see [`GET /v1/gateway/groups/{group_id}/api_keys`](/reference/gateway/api-keys/list-api-keys-for-a-group) and [`GET /v1/gateway/groups/{group_id}/api_keys/{api_key_prefix}`](/reference/gateway/api-keys/get-an-api-key).

## Revoke a key

Revoke a key to cut off a single credential, for example when a customer rotates out or a key leaks. Other keys under the same group are unaffected.

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request DELETE \
    --url https://api.baseten.co/v1/gateway/groups/abc123hash/api_keys/sky_sCqhBwEy4kPd \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```

  ```json Output theme={"system"}
  {
    "prefix": "sky_sCqhBwEy4kPd"
  }
  ```
</CodeGroup>

<Warning>
  Revocation is irreversible. After this call, the key can't authenticate any request and can't be restored. To restore access for the same downstream customer, mint a new key under the same group.
</Warning>

For more information, see [`DELETE /v1/gateway/groups/{group_id}/api_keys/{api_key_prefix}`](/reference/gateway/api-keys/revoke-an-api-key).

## Delete a group

Delete a group when a downstream customer churns. The call removes the group, revokes every API key in the group, and recursively removes every descendant group and their keys. The `external_entity_id` is freed for reuse; you can call `POST /v1/gateway/groups` again with the same value to provision a fresh group.

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request DELETE \
    --url https://api.baseten.co/v1/gateway/groups/abc123hash \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```

  ```json Output theme={"system"}
  {
    "id": "abc123hash",
    "metadata": {
      "name": "Acme prod",
      "external_entity_id": "cust_42"
    },
    "deleted_at": "2026-05-13T12:34:56Z"
  }
  ```
</CodeGroup>

To revoke a single key without churning the whole group, use [Revoke a key](#revoke-a-key) instead.

For more information, see [`DELETE /v1/gateway/groups/{group_id}`](/reference/gateway/groups/delete-a-group).

## Next steps

* **[Rate and usage limits](/frontier-gateway/rate-limits)**: Token and request thresholds, inheritance modes, and 429 behavior.
* **[Billing webhooks](/frontier-gateway/billing-webhooks)**: Stream signed per-request usage events into your billing pipeline.
