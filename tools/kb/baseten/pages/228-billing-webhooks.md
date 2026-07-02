# Billing webhooks
Source: https://docs.baseten.co/reference/gateway/billing-webhooks

Payload, header, and signature reference for Frontier Gateway billing webhooks.

Frontier Gateway delivers a signed webhook to your configured endpoint for each inference request through the gateway. This is a webhook delivered to your endpoint, not an endpoint you call. Delivery is gated to workspaces onboarded to Frontier Gateway. For the consumption guide (verification snippets, retry semantics, and recommended consumption pattern), see [Billing webhooks](/frontier-gateway/billing-webhooks).

## Event type

Frontier Gateway emits a single event type today: `API_BILLING_USAGE`. The payload uses the standard Baseten envelope, where `type` is the discriminator and `data` holds the event-specific fields.

<ResponseField name="type" type="string">
  Event type discriminator. Always `"API_BILLING_USAGE"` for Frontier Gateway billing events.
</ResponseField>

<ResponseField name="data" type="object">
  Event-specific payload.

  * **events** (`array`, required): One or more event entries per delivery. Each entry corresponds to a single inference request through the gateway. See **Event fields** below for the entry shape.
</ResponseField>

## Event fields

Each entry in `data.events[]` describes one inference request. Payloads may carry fields beyond those documented here; ignore them, as they're internal and can change without notice.

<ResponseField name="idempotencyKey" type="string">
  Stable identifier for the event. Use this to deduplicate on your side; the same key never describes two distinct events. Stable across retries of the same delivery.
</ResponseField>

<ResponseField name="timestamp" type="string">
  ISO 8601 UTC timestamp of the inference request, for example `"2025-07-07T23:40:35.905Z"`.
</ResponseField>

<ResponseField name="requestId" type="string">
  Per-request identifier, useful for correlating billing events with platform logs.
</ResponseField>

<ResponseField name="requestMetadata" type="object | null">
  Freeform JSON object passed through from the inference request. May be `null` when no metadata is supplied.
</ResponseField>

<ResponseField name="modelSlug" type="string">
  Slug of the model invoked, in `your-org/your-model` form.
</ResponseField>

<ResponseField name="externalEntityId" type="string">
  The `metadata.external_entity_id` of the group that owns the key used for the request, the same value you write when you call [`POST /v1/gateway/groups`](/reference/gateway/groups/create-a-group).
</ResponseField>

<ResponseField name="apiKeyPrefix" type="string">
  Prefix of the federated API key that made the request (the substring before the `.` in the full key string). Use it to attribute usage to a specific key within the group. See [Manage groups and API keys](/frontier-gateway/api-keys).
</ResponseField>

<ResponseField name="tokens" type="object">
  Token counts for the request.

  * **inputTokens** (`integer`, required): Prompt tokens consumed by the request.
  * **outputTokens** (`integer`, required): Generated tokens returned by the model.
  * **cachedInputTokens** (`integer`, required): Prompt tokens served from cache, when applicable.
</ResponseField>

## Headers

Baseten sets two headers on every delivery.

<ResponseField name="X-Baseten-Signature" type="string">
  HMAC-SHA256 signature of the raw request body, in `v1=<hex>` format, computed with your workspace's webhook signing secret. Verify this on every delivery before trusting the payload. For more information, see [Verify the signature](/frontier-gateway/billing-webhooks#verify-the-signature).
</ResponseField>

<ResponseField name="X-Baseten-Request-ID" type="string">
  UUID generated per outbound delivery. Reused across retry attempts of the same delivery, so it's useful as a correlation ID against Baseten platform logs but not as a deduplication key. Use `idempotencyKey` to dedupe events.
</ResponseField>

## Signature format

The `X-Baseten-Signature` header has the format `v1=<hex>`, where `<hex>` is the HMAC-SHA256 of the raw request body computed with your workspace's webhook signing secret. Compute the HMAC against the **raw request bytes**, not a re-serialized JSON, and compare in constant time. For runnable verification snippets in Python and Node.js, see [Verify the signature](/frontier-gateway/billing-webhooks#verify-the-signature).

## Sample payload

```json theme={"system"}
{
  "type": "API_BILLING_USAGE",
  "data": {
    "events": [
      {
        "idempotencyKey": "01J9X7Y0Z3K4M5N6P7Q8R9S0T1",
        "timestamp": "2025-07-07T23:40:35.905Z",
        "requestId": "5e4a8c1a-2b3c-4d5e-9f0a-1b2c3d4e5f6a",
        "requestMetadata": {},
        "modelSlug": "your-org/your-model",
        "externalEntityId": "cust_42",
        "apiKeyPrefix": "sky_sCqhBwEy4kPd",
        "tokens": {
          "inputTokens": 100,
          "outputTokens": 200,
          "cachedInputTokens": 300
        }
      }
    ]
  }
}
```
