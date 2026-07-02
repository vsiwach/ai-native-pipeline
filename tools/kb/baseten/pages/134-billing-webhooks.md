# Billing webhooks
Source: https://docs.baseten.co/frontier-gateway/billing-webhooks

Receive signed per-request usage events from Frontier Gateway and pipe them into your billing provider out-of-band from the inference path.

For each inference request through Baseten Frontier Gateway, Baseten emits a signed webhook to your endpoint with token counts, the calling group's external identifier, the API key that made the request, and request metadata. You can consume these events to meter usage in Stripe, Orb, or your own billing system without sitting in the request path. Webhook delivery is configured per workspace during managed onboarding: your Baseten team provisions the target URL and webhook signing secret before your first event ships.

## Payload

Baseten POSTs a JSON body to your configured webhook URL. Every payload uses the standard Baseten envelope, where `type` is the discriminator and `data` holds the event-specific fields. Frontier Gateway emits the `API_BILLING_USAGE` event type; future event types may share the same envelope.

The `data.events` array can contain one or more events per delivery. Each event corresponds to a single inference request. Payloads may carry fields beyond those documented here; ignore them, as they're internal and can change without notice.

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

Fields on each event:

<ParamField type="string">
  Stable identifier for the event. Use this to deduplicate on your side.
</ParamField>

<ParamField type="string">
  ISO 8601 UTC timestamp of the inference request.
</ParamField>

<ParamField type="string">
  Per-request identifier, useful for correlating billing events with platform logs.
</ParamField>

<ParamField type="object | null">
  Freeform JSON object passed through from the inference request. May be `null` when no metadata is supplied.
</ParamField>

<ParamField type="string">
  The model slug invoked, in `your-org/your-model` form.
</ParamField>

<ParamField type="string">
  The `metadata.external_entity_id` you set on the group that owns the key used for the request, the same value you write when you [create or update the group](/frontier-gateway/api-keys#create-a-group).
</ParamField>

<ParamField type="string">
  Prefix of the federated API key that made the request (the substring before the `.` in the full key string). The group identifies your customer; the prefix identifies which of that customer's [keys](/frontier-gateway/api-keys) drove the usage.
</ParamField>

<ParamField type="object">
  Token counts for the request.

  * **inputTokens** (`integer`, required): Prompt tokens.
  * **outputTokens** (`integer`, required): Generated tokens.
  * **cachedInputTokens** (`integer`, required): Prompt tokens served from cache, when applicable.
</ParamField>

## Headers

Baseten sets two headers on every delivery:

* `X-Baseten-Signature`: HMAC signature of the raw request body. For more information, see [Verify the signature](#verify-the-signature).
* `X-Baseten-Request-ID`: UUID generated per outbound delivery. Log this on your receiver as a correlation ID for debugging against Baseten platform logs. Use `idempotencyKey`, not this header, to dedupe events on your side; the same `requestId` is reused across retry attempts of a single delivery.

## Verify the signature

The `X-Baseten-Signature` header has the format `v1=<hex>`, where `<hex>` is the HMAC-SHA256 of the raw request body computed with your workspace's webhook signing secret. Verify the signature on every request before trusting the payload.

Two requirements:

* Verify against the **raw bytes** of the request body, not a re-serialized version. JSON re-serialization changes whitespace and field order and breaks the HMAC.
* Use a constant-time comparison (`hmac.compare_digest` in Python, `crypto.timingSafeEqual` in Node.js) to avoid timing attacks.

<Tabs>
  <Tab title="Python">
    ```python verify.py theme={"system"}
    import hmac
    import hashlib
    import os

    def verify_signature(request) -> bool:
        signing_secret = os.getenv("BASETEN_WEBHOOK_SIGNING_SECRET")
        signature = request.headers.get("X-Baseten-Signature")
        body = request.data

        mac = hmac.new(signing_secret.encode("utf-8"), body, hashlib.sha256)
        expected_signature = f"v1={mac.hexdigest()}"
        return hmac.compare_digest(expected_signature, signature)
    ```
  </Tab>

  <Tab title="Node.js">
    ```javascript verify.js theme={"system"}
    import crypto from "node:crypto";

    export function verifySignature(rawBody, signatureHeader) {
      const signingSecret = process.env.BASETEN_WEBHOOK_SIGNING_SECRET;
      const mac = crypto.createHmac("sha256", signingSecret);
      mac.update(rawBody);
      const expected = `v1=${mac.digest("hex")}`;

      const expectedBuf = Buffer.from(expected);
      const actualBuf = Buffer.from(signatureHeader ?? "");
      if (expectedBuf.length !== actualBuf.length) {
        return false;
      }
      return crypto.timingSafeEqual(expectedBuf, actualBuf);
    }
    ```
  </Tab>
</Tabs>

Webhook signing secrets are a general Baseten primitive shared across products that emit signed webhooks. Your Frontier Gateway secret is provisioned during onboarding. For rotation behavior, see [Secure webhooks](/inference/async#secure-webhooks).

## Delivery semantics

Baseten retries failed deliveries with exponential backoff so a transient blip on your endpoint doesn't drop billing events. Use these numbers to size your endpoint SLOs and to know when a failure is terminal.

* **Per-attempt timeout**: 10 seconds. If your endpoint doesn't respond within this window, Baseten cancels the attempt and treats it as a failure.
* **Backoff**: Exponential, starting at 1 second between attempts and capping at 5 seconds.
* **Maximum elapsed time**: 15 seconds. After this, Baseten stops retrying and routes the event to a dead-letter queue. The retry window is tight: the realistic budget is one or two attempts.
* **4xx responses are terminal**: Any 4xx status from your endpoint stops retries immediately. Only 5xx responses, network errors, and timeouts trigger a retry.

Events that exhaust retries land in the dead-letter queue and are not redelivered automatically. Contact your Baseten team to recover events from the DLQ.

## Recommended consumption pattern

Treat the webhook handler as an ingestion endpoint, not a billing pipeline. The handler's job is to durably accept the event and return as fast as possible.

1. Verify the signature.
2. Persist the event to your own queue or database, keyed on `idempotencyKey`.
3. Return a 2xx response.
4. Process and forward to your billing provider asynchronously.

This separates two failure modes: receiving the event from Baseten, and reconciling it with your billing provider. If your billing provider is slow or down, you don't drop events or block the gateway's retry timer.

<Warning>
  Acknowledge fast. If your handler runs billing logic inline and exceeds the 10-second per-attempt timeout, Baseten retries the delivery and you risk double-billing your customer. The total retry window is only 15 seconds, so a slow handler that survives the first timeout often misses the retry budget entirely and lands in the DLQ. Always return 2xx before doing slow work, and dedupe on `idempotencyKey` to handle the at-least-once delivery guarantee.
</Warning>

## Next steps

* **[Manage groups and API keys](/frontier-gateway/api-keys)**: Create groups, build a hierarchy, mint and revoke keys, and delete groups.
* **[Rate and usage limits](/frontier-gateway/rate-limits)**: Cap per-group, per-model token and request volume.
