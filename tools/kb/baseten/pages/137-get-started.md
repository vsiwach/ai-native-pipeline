# Get started
Source: https://docs.baseten.co/frontier-gateway/get-started

Create an endpoint, create a group, mint an API key, and call your model through the gateway.

By the end of this guide, you'll have created an endpoint that routes a slug to your deployment, created a Frontier Gateway group for one of your downstream customers, minted an API key bound to that group, and called your Dedicated deployment through the gateway with the key. From here, you can build a deeper group hierarchy, configure additional rate and usage limits, set up billing webhooks, and explore the full lifecycle.

## Prerequisites

* A [Dedicated deployment](/deployment/concepts) of your model on Baseten.
* A [Baseten workspace API key](/organization/api-keys) with management scope, exported as `BASETEN_API_KEY`.
* Completed Frontier Gateway onboarding with your Baseten team.

This guide assumes you've finished managed onboarding: your workspace is provisioned for federated keys, and your webhook signing secret is in place. If you haven't started yet, [talk to us](https://www.baseten.co/talk-to-us/). The `/v1/gateway/` endpoints used here return `403` to workspaces that aren't onboarded.

## Create an endpoint

An **endpoint** maps a routing slug to one of your deployments. Your customers call the slug, and the gateway routes the request to the target you set here. The slug has the form `{org_prefix}/{name}`, where `org_prefix` is a prefix your organization owns. The Baseten team registers your prefixes during onboarding; registering or updating a prefix isn't a self-service action.

Create an endpoint with `POST /v1/gateway/endpoints`. The body takes the `slug` and a `targets` list with one Baseten target: the `model_id` of the deployment that should serve the slug. The response includes the endpoint `id` and confirms the slug now routes to your deployment; you'll reference this same slug when you create a group.

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request POST \
    --url https://api.baseten.co/v1/gateway/endpoints \
    --header "Authorization: Api-Key $BASETEN_API_KEY" \
    --header "Content-Type: application/json" \
    --data '{
      "slug": "your-org/your-model",
      "targets": [
        {
          "provider": "BASETEN",
          "model_id": "3kZ9xqd"
        }
      ]
    }'
  ```

  ```json Output theme={"system"}
  {
    "id": "abc123hash",
    "slug": "your-org/your-model",
    "targets": [
      { "provider": "BASETEN", "model_id": "3kZ9xqd" }
    ],
    "created_at": "2026-06-17T12:00:00Z",
    "updated_at": "2026-06-17T12:00:00Z"
  }
  ```
</CodeGroup>

For the full lifecycle, including how to re-point or delete an endpoint, see [Endpoints](/frontier-gateway/endpoints).

## Create a group

A **group** is the resource you create per customer, plan, project, or whichever unit of your organizational hierarchy maps to a billing or access boundary. The group owns an external identifier (your stable ID for this entity), the model slugs it's allowed to call, and the rate and usage limits enforced on every call. List the slug from the endpoint you created earlier so the group can call it. API keys are minted under the group next.

Create a group with `POST /v1/gateway/groups`. The request takes a `metadata` block (display name plus the external identifier), a non-empty `models` list pairing each model slug with its rate and usage limits, and a `hierarchy` block declaring the inheritance mode and an optional parent. This example creates a top-level (root) group with independent enforcement. The response is the new group, including the internal `id` you'll use as the path parameter when minting keys.

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

Save the `id`. You'll need it when you mint a key. The `effective_models` block shows the limits the runtime enforces after inheritance; for a root group it matches `models` exactly. See [Rate and usage limits](/frontier-gateway/rate-limits#effective-limits-and-inheritance) for how this changes once you add a parent.

## Mint an API key for the group

Issue a new API key under the group with `POST /v1/gateway/groups/{group_id}/api_keys`. The key inherits the group's effective model set and limits; you don't configure either on the key itself. The response contains the plaintext key, returned exactly once.

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

The string before the `.` (here, `sky_sCqhBwEy4kPd`) is the **prefix**. You'll use the prefix, not the full key, when fetching or revoking the key later.

## Call your model through the gateway

Use the API key you minted to call your model. Frontier Gateway is OpenAI-compatible, so the OpenAI SDK works with the gateway base URL. Replace `YOUR_API_KEY` in the examples below with the value you saved from the mint-key response.

<Tabs>
  <Tab title="Python">
    Install the OpenAI SDK:

    ```bash theme={"system"}
    pip install openai
    ```

    Make a chat completion request:

    ```python chat.py theme={"system"}
    from openai import OpenAI

    client = OpenAI(
        base_url="https://inference.baseten.co/v1",
        api_key="YOUR_API_KEY",
    )

    response = client.chat.completions.create(
        model="your-org/your-model",
        messages=[{"role": "user", "content": "Hello, world!"}],
    )

    print(response.choices[0].message.content)
    ```
  </Tab>

  <Tab title="curl">
    ```bash theme={"system"}
    curl --request POST \
      --url https://inference.baseten.co/v1/chat/completions \
      --header "Content-Type: application/json" \
      --header "Authorization: Api-Key YOUR_API_KEY" \
      --data '{
        "model": "your-org/your-model",
        "messages": [
          {"role": "user", "content": "Hello, world!"}
        ]
      }'
    ```
  </Tab>
</Tabs>

The response follows the standard OpenAI Chat Completions schema:

```json Output theme={"system"}
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "your-org/your-model",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 9,
    "total_tokens": 19
  }
}
```

The base URL is `https://inference.baseten.co/v1` today. Once white-label routing is provisioned for your workspace, the base URL becomes the branded domain you configure with your Baseten team, and your downstream customers call your domain instead.

## Next steps

* **[Manage groups and API keys](/frontier-gateway/api-keys)**: Build a multi-level hierarchy, mint and revoke keys, and delete groups.
* **[Rate and usage limits](/frontier-gateway/rate-limits)**: Tune per-group, per-model thresholds and pick an inheritance mode.
* **[Billing webhooks](/frontier-gateway/billing-webhooks)**: Stream signed per-request usage events into your billing pipeline.
