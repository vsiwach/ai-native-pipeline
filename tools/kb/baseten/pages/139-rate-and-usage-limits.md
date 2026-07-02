# Rate and usage limits
Source: https://docs.baseten.co/frontier-gateway/rate-limits

Per-group, per-model token and request limits, two inheritance modes, and how Frontier Gateway computes the effective limits the runtime enforces.

<FrontierGatewayBudgetLedgerEngine />

In Frontier Gateway, rate and usage limits live on the **group**, not on individual API keys. Every key minted under a group inherits the group's effective limits, so rotating a customer's credentials doesn't change what they can spend. Rate limits cap short-window throughput (per second or per minute), and usage limits cap total consumption per daily window. Both are scoped to a single (group, model slug) pair, so a group can carry separate limits for every model its keys are allowed to call.

You configure both kinds of limit by passing them inside `models[].rate_limits` and `models[].usage_limits` when you call [`POST /v1/gateway/groups`](/reference/gateway/groups/create-a-group) or [`PATCH /v1/gateway/groups/{group_id}`](/reference/gateway/groups/update-a-group). Workspace API keys and the shared Model APIs product use a different limit model; for the comparison, see [Frontier Gateway versus Model APIs limits](#frontier-gateway-versus-model-apis-limits).

## Rate limits

A rate limit caps short-window throughput. You attach one or more rate limits to each model slug on a group.

| Field       | Values             | Description                                                           |
| ----------- | ------------------ | --------------------------------------------------------------------- |
| `type`      | `TOKEN`, `REQUEST` | Whether the limit counts tokens (prompt plus completion) or requests. |
| `unit`      | `SECOND`, `MINUTE` | The window the threshold applies to.                                  |
| `threshold` | Integer `>= 1`     | The maximum count allowed per window.                                 |

You can set both a `TOKEN` and a `REQUEST` rate limit on the same model slug, but you can't set two rate limits with the same `type`.

```json theme={"system"}
{
  "metadata": { "external_entity_id": "cust_42" },
  "models": [
    {
      "slug": "your-org/your-model",
      "rate_limits": [
        { "type": "TOKEN", "unit": "MINUTE", "threshold": 1000000 },
        { "type": "REQUEST", "unit": "MINUTE", "threshold": 100 }
      ]
    }
  ],
  "hierarchy": { "limit_enforcement": "INDEPENDENT", "parent_group_id": null }
}
```

In this example, the group can spend up to one million prompt-plus-completion tokens per minute on `your-org/your-model`, and up to 100 requests per minute against the same model. Both ceilings are enforced; whichever the caller hits first triggers a `429 Too Many Requests` response.

## Usage limits

A usage limit caps how much a group can spend in a daily window. Usage limits are optional. You can attach a usage limit to any model slug the group is allowed to call.

| Field       | Values             | Description                                                              |
| ----------- | ------------------ | ------------------------------------------------------------------------ |
| `type`      | `TOKEN`, `REQUEST` | Whether the limit counts tokens or requests.                             |
| `unit`      | `DAY`              | The window the threshold applies to. Daily is the only supported window. |
| `threshold` | Integer `>= 1`     | The maximum count allowed per daily window.                              |

Both `TOKEN` and `REQUEST` are supported as the `type` for a usage limit:

```json theme={"system"}
{
  "models": [
    {
      "slug": "your-org/your-model",
      "usage_limits": [
        { "type": "TOKEN", "unit": "DAY", "threshold": 10000000 },
        { "type": "REQUEST", "unit": "DAY", "threshold": 5000 }
      ]
    }
  ]
}
```

In this example, the group can spend up to ten million tokens per day and up to 5,000 requests per day on `your-org/your-model`. Whichever ceiling the caller hits first triggers a `429 Too Many Requests` response for the rest of the daily window.

## Per-model scope

Limits are scoped per (group, model slug) pair. A group can be authorized for multiple model slugs, and each slug carries its own independent rate-limit and usage-limit buckets. Spending tokens against one model doesn't draw down another model's budget on the same group.

```json theme={"system"}
{
  "models": [
    {
      "slug": "your-org/your-model",
      "rate_limits": [
        { "type": "TOKEN", "unit": "MINUTE", "threshold": 1000000 }
      ],
      "usage_limits": [
        { "type": "TOKEN", "unit": "DAY", "threshold": 10000000 }
      ]
    },
    {
      "slug": "your-org/your-other-model",
      "rate_limits": [
        { "type": "REQUEST", "unit": "SECOND", "threshold": 20 }
      ]
    }
  ]
}
```

In this example, `your-org/your-model` carries a per-minute token rate limit and a daily token usage limit, while `your-org/your-other-model` carries only a per-second request rate limit. The two slugs are independent.

## Inheritance modes

Every group declares an enforcement mode at creation by setting `hierarchy.limit_enforcement` to one of two values: `INDEPENDENT` or `CASCADING`. The mode controls how a child group's usage interacts with its ancestors. The mode is fixed for the whole hierarchy: children must declare the same mode as their parent, and the field is immutable after creation. Hierarchies are capped at five levels deep.

### Independent mode

In an independent hierarchy, a child group inherits any limit its ancestors set when the child omits it, but the child's usage is metered separately from its ancestors. A child can override an inherited threshold upward or downward. A sibling's traffic never draws down another sibling's budget.

Think of an independent hierarchy as a template. The parent group establishes default limits, and children opt out of them by declaring their own. Consumption is bucketed per group, with no cross-group accounting.

Worked example. A root group `free-tier` has:

```json theme={"system"}
{ "type": "TOKEN", "unit": "MINUTE", "threshold": 100000000 }
```

A child group `john` under `free-tier` declares no limits. The runtime enforces 100M TPM on `john`, sourced from `free-tier`. If you later raise `free-tier`'s threshold to 150M TPM, `john` automatically gets 150M TPM too.

A sibling child group `sally` under `free-tier` declares its own ceiling:

```json theme={"system"}
{ "type": "TOKEN", "unit": "MINUTE", "threshold": 120000000 }
```

The runtime enforces 120M TPM on `sally`, sourced from `sally`. `john`'s traffic doesn't draw down `sally`'s budget, and `sally`'s traffic doesn't draw down `john`'s.

### Cascading mode

In a cascading hierarchy, a child group's usage counts against every ancestor at the same time. A request that fits the child's own limit can still be rejected if an ancestor is exhausted.

Think of a cascading hierarchy as a shared pool. An ancestor establishes a hard cap on the subtree's total consumption, and children divide it. Siblings can compete for the same pool: one sibling spending heavily reduces what's available to the others.

Children in a cascading hierarchy can't declare a threshold higher than any ancestor's threshold for the same (slug, type, unit) tuple. Frontier Gateway enforces this at write time, on both create and update. Any of the following requests fails with `400 Bad Request: "Child group exceeds parent group limit."`:

* Creating a child whose declared threshold exceeds an ancestor's threshold for the same (slug, type, unit).
* Raising a descendant's threshold past an ancestor's with `PATCH`.
* Lowering an ancestor's threshold with `PATCH` below the highest existing descendant threshold.

To raise a subtree's ceiling, raise the ancestor first, then the descendants. To lower an ancestor below a descendant, lower the descendant first. Each direction is rejected if you do it out of order.

Worked example. A root group `org` has:

```json theme={"system"}
{ "type": "TOKEN", "unit": "MINUTE", "threshold": 100000000 }
```

Two children `finance` and `engineering` under `org` each declare:

```json theme={"system"}
{ "type": "TOKEN", "unit": "MINUTE", "threshold": 70000000 }
```

Each child's `effective_models` shows 70M TPM sourced from itself, but the runtime also enforces the 100M TPM ceiling sourced from `org` against the **combined** traffic of `finance` and `engineering`. If `finance` consumes 70M in a given minute, `engineering` has only 30M of headroom left in that minute, regardless of its own declared 70M ceiling. The 70M + 70M over-provisioning is allowed at create time because each individual child threshold (70M) stays at or below the parent's (100M); only a single child threshold that exceeded the parent's would be rejected.

The following chart traces that same minute. `finance` consumes its full 70M ceiling, dropping the `org` pool from 100M to 30M, then `engineering` hits `429` after 30M of accepted traffic with 40M of its own 70M ceiling still untouched.

<FrontierGatewayBudgetLedger />

### Effective limits and inheritance

Every group response carries two parallel blocks:

* **`models`**: the configuration you wrote on this specific group, as if you were reading the row alone.
* **`effective_models`**: the limits the runtime enforces on this group after walking the hierarchy. Each limit carries a `source_group` field pointing to the group (this one or an ancestor) the limit is anchored to.

In an independent hierarchy, `effective_models` resolves each (slug, type, unit) tuple by taking the closest ancestor (including self) that declared it.

In a cascading hierarchy, `effective_models` lists every distinct ancestor limit the request is subject to. Read it as the full set of ceilings that gate this group's traffic.

`effective_models` is read-only. To change what a group enforces, update the `models` block on the group itself (or on an ancestor) with `PATCH /v1/gateway/groups/{group_id}`.

## Enforcement and reset

When a request from one of a group's keys exceeds any limit on the request's `effective_models` for the requested model slug, the platform rejects the request with `429 Too Many Requests`. The 429 fires for the first limit hit: if a group has a `TOKEN/MINUTE` rate limit and a `REQUEST/DAY` usage limit, either can trigger rejection. In a cascading hierarchy, the limit hit can be one anchored on an ancestor rather than the calling group's own configuration.

Daily usage windows reset at midnight UTC. After reset, a group's consumption for each `DAY` limit returns to zero and the group can spend up to the threshold again over the next 24 hours.

Rate-limit windows (per second, per minute) are short rolling windows enforced inline on every request and don't have a reset timestamp you need to track.

## Current consumption

To inspect a group's usage against its configured `usage_limits` without waiting for a 429, call `GET /v1/gateway/groups/{group_id}/usage`. The response returns one entry per `(model slug, type, unit)` tuple the group has a usage limit on, with the configured `threshold`, the `current_usage` in the active daily window, and the `reset_at` timestamp for that window.

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request GET \
    --url https://api.baseten.co/v1/gateway/groups/abc123hash/usage \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```

  ```json Output theme={"system"}
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
</CodeGroup>

Only models that have `usage_limits` configured on the group's effective configuration appear in the response. Rate-limit consumption isn't surfaced through this endpoint; rate limits are short rolling windows and don't carry a stored counter. For the full response shape, see [Get group usage](/reference/gateway/groups/get-group-usage).

## Frontier Gateway versus Model APIs limits

Frontier Gateway and the shared Model APIs product use different limit models:

* **Frontier Gateway** limits are **per group, per model slug**, with an inheritance mode picked at the root. You configure `TOKEN`/`REQUEST` rate limits (`SECOND` or `MINUTE`) and optional `TOKEN`/`REQUEST` usage limits (`DAY`) on the group, and every key minted under the group inherits the group's effective config.
* **Model APIs** limits are **account-tier RPM/TPM** ceilings that apply to your workspace API key as a whole, regardless of which Model APIs model you're calling.

For more information on Model APIs limits, see [Rate limits and budgets](/inference/model-apis/rate-limits-and-budgets).

## Next steps

* **[Manage groups and API keys](/frontier-gateway/api-keys)**: Configure limits when you create or update a group, and rotate keys without changing them.
