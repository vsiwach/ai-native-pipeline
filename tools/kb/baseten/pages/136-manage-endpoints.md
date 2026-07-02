# Manage endpoints
Source: https://docs.baseten.co/frontier-gateway/endpoints

Create and manage the endpoints that route Frontier Gateway traffic to your Baseten deployments.

An **endpoint** is the routing slug your customers call, like `my-org/glm-5.2`, plus the target it points to. When a request reaches the gateway with that slug, the gateway routes it to the target. You manage endpoints yourself through the [REST API](/reference/gateway/overview), so you can stand up a new slug, re-point it at a different deployment, or retire it.

<Note>
  To enable Frontier Gateway for your workspace, [talk to us](https://www.baseten.co/talk-to-us/).
</Note>

## Concepts

An endpoint has two parts:

* **Slug**: a globally-unique routing identifier of the form `{org_prefix}/{name}`, such as `my-org/glm-5.2`, where the prefix is one your organization owns. You can rename a slug as long as the new value is globally unique and keeps a prefix your organization owns.
* **Target**: where the slug routes. A target is either a Baseten deployment (`provider: BASETEN`, with the `model_id` it should serve and optional `environment_name`) or an external model provider such as Anthropic (`provider: ANTHROPIC`) or OpenAI (`provider: OPENAI`). An endpoint takes a list of targets but holds exactly one today.

### Endpoints and groups

Endpoints and [groups](/frontier-gateway/api-keys) answer two different questions:

* An **endpoint** defines *what a slug routes to*: which deployment serves traffic for `my-org/glm-5.2`.
* A **group** defines *who can call a slug and how much*: the model slugs a federated key may call, plus its rate and usage limits.

To serve a model to a customer, create an endpoint for the slug, then grant a group access to that same slug and mint the customer a key under it. The slug ties the two together.

## Create an endpoint

Create an endpoint to give your customers a stable slug to call that routes to one of your deployments. The request body takes the `slug` and a `targets` list with one Baseten target. Omit `environment_name` to use production, or pass a non-production environment such as `staging`. The response is the new endpoint; save the `id`, which is the path parameter for every per-endpoint operation that follows.

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request POST \
    --url https://api.baseten.co/v1/gateway/endpoints \
    --header "Authorization: Api-Key $BASETEN_API_KEY" \
    --header "Content-Type: application/json" \
    --data '{
      "slug": "my-org/glm-5.2",
      "targets": [
        {
          "provider": "BASETEN",
          "model_id": "3kZ9xqd",
          "environment_name": "staging"
        }
      ]
    }'
  ```

  ```json Output theme={"system"}
  {
    "id": "abc123hash",
    "slug": "my-org/glm-5.2",
    "targets": [
      {
        "provider": "BASETEN",
        "model_id": "3kZ9xqd",
        "environment_name": "staging"
      }
    ],
    "created_at": "2026-06-17T12:00:00Z",
    "updated_at": "2026-06-17T12:00:00Z"
  }
  ```
</CodeGroup>

For more information, see [`POST /v1/gateway/endpoints`](/reference/gateway/endpoints/create-an-endpoint).

## List endpoints

List your endpoints to see every slug you've published and where each one routes. Results are cursor-paginated: pass `limit` and `cursor` query parameters to page through results, and follow `pagination.cursor` while `pagination.has_more` is `true`.

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request GET \
    --url https://api.baseten.co/v1/gateway/endpoints \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```

  ```json Output theme={"system"}
  {
    "items": [
      {
        "id": "abc123hash",
        "slug": "my-org/glm-5.2",
        "targets": [
          {
            "provider": "BASETEN",
            "model_id": "3kZ9xqd",
            "environment_name": "staging"
          }
        ],
        "created_at": "2026-06-17T12:00:00Z",
        "updated_at": "2026-06-17T12:00:00Z"
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
    --url "https://api.baseten.co/v1/gateway/endpoints?cursor=aVd2Yk54T2d2V0dFWE13R1l4R2k5UVE=" \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```

  ```json Output theme={"system"}
  {
    "items": [
      {
        "id": "def456hash",
        "slug": "my-org/glm-5.2-canary",
        "targets": [
          {
            "provider": "BASETEN",
            "model_id": "7mP2wqe",
            "environment_name": "staging"
          }
        ],
        "created_at": "2026-06-17T12:05:00Z",
        "updated_at": "2026-06-17T12:05:00Z"
      }
    ],
    "pagination": {
      "has_more": false,
      "cursor": null
    }
  }
  ```
</CodeGroup>

For more information, see [`GET /v1/gateway/endpoints`](/reference/gateway/endpoints/list-endpoints).

## Get an endpoint

Get an endpoint by its `id` to check where a single slug currently routes, for example to confirm a change took effect.

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request GET \
    --url https://api.baseten.co/v1/gateway/endpoints/abc123hash \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```

  ```json Output theme={"system"}
  {
    "id": "abc123hash",
    "slug": "my-org/glm-5.2",
    "targets": [
      {
        "provider": "BASETEN",
        "model_id": "3kZ9xqd",
        "environment_name": "staging"
      }
    ],
    "created_at": "2026-06-17T12:00:00Z",
    "updated_at": "2026-06-17T12:00:00Z"
  }
  ```
</CodeGroup>

For more information, see [`GET /v1/gateway/endpoints/{endpoint_id}`](/reference/gateway/endpoints/get-an-endpoint).

## Re-point an endpoint

Re-point an endpoint to move a live slug to a different deployment, like promoting a new model version, without asking your customers to change the name they call. The slug stays the same; you replace the endpoint's full target list. The gateway syncs endpoints every 60 seconds, so a change can take up to a minute to take effect.

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request PATCH \
    --url https://api.baseten.co/v1/gateway/endpoints/abc123hash \
    --header "Authorization: Api-Key $BASETEN_API_KEY" \
    --header "Content-Type: application/json" \
    --data '{
      "targets": [
        {
          "provider": "BASETEN",
          "model_id": "7mP2wqe",
          "environment_name": "staging"
        }
      ]
    }'
  ```

  ```json Output theme={"system"}
  {
    "id": "abc123hash",
    "slug": "my-org/glm-5.2",
    "targets": [
      {
        "provider": "BASETEN",
        "model_id": "7mP2wqe",
        "environment_name": "staging"
      }
    ],
    "created_at": "2026-06-17T12:00:00Z",
    "updated_at": "2026-06-17T13:30:00Z"
  }
  ```
</CodeGroup>

For more information, see [`PATCH /v1/gateway/endpoints/{endpoint_id}`](/reference/gateway/endpoints/replace-endpoint-targets).

## Delete an endpoint

Delete an endpoint to take a slug out of service, whether you're retiring a model or freeing the slug for reuse. The gateway stops routing the slug.

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request DELETE \
    --url https://api.baseten.co/v1/gateway/endpoints/abc123hash \
    --header "Authorization: Api-Key $BASETEN_API_KEY"
  ```

  ```json Output theme={"system"}
  {
    "id": "abc123hash",
    "slug": "my-org/glm-5.2"
  }
  ```
</CodeGroup>

For more information, see [`DELETE /v1/gateway/endpoints/{endpoint_id}`](/reference/gateway/endpoints/delete-an-endpoint).

## Next steps

* **[Manage groups and API keys](/frontier-gateway/api-keys)**: Grant a group access to your endpoint's slug and mint a key for it.
* **[Rate and usage limits](/frontier-gateway/rate-limits)**: Control per-group, per-model usage on the slug.
* **[Endpoints API reference](/reference/gateway/endpoints/create-an-endpoint)**: Full request and response shapes for every endpoint operation.
