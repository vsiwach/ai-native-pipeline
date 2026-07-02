# Overview
Source: https://docs.baseten.co/reference/gateway/overview

Manage Frontier Gateway endpoints, groups, and federated API keys through the Baseten REST API.

The Frontier Gateway API manages the resources behind your branded inference gateway: the **endpoints** that route slugs to deployments, the **groups** that model your customers and their limits, and the **federated API keys** your customers call with. For the conceptual guide and end-to-end examples, see the [Frontier Gateway overview](/frontier-gateway/overview).

These endpoints live under `/v1/gateway/` and are gated to Frontier Gateway workspaces. Authenticate with a workspace API key with management scope, passed as `Authorization: Api-Key $BASETEN_API_KEY`. Requests from workspaces that aren't onboarded return `403`. The full OpenAPI spec is available at [api.baseten.co/v1/spec](https://api.baseten.co/v1/spec) for generating API clients.

## Endpoints

An endpoint maps a routing slug to the deployment that serves it. Use these routes to create, inspect, re-point, and delete endpoints.

| Method   | Endpoint                                                                                       | Description        |
| :------- | :--------------------------------------------------------------------------------------------- | :----------------- |
| `POST`   | [`/v1/gateway/endpoints`](/reference/gateway/endpoints/create-an-endpoint)                     | Create an endpoint |
| `GET`    | [`/v1/gateway/endpoints`](/reference/gateway/endpoints/list-endpoints)                         | List endpoints     |
| `GET`    | [`/v1/gateway/endpoints/{endpoint_id}`](/reference/gateway/endpoints/get-an-endpoint)          | Get an endpoint    |
| `PATCH`  | [`/v1/gateway/endpoints/{endpoint_id}`](/reference/gateway/endpoints/replace-endpoint-targets) | Update an endpoint |
| `DELETE` | [`/v1/gateway/endpoints/{endpoint_id}`](/reference/gateway/endpoints/delete-an-endpoint)       | Delete an endpoint |

## Groups

A group owns the model set, rate and usage limits, and place in the hierarchy that its keys inherit. Use these routes to manage groups and inspect their usage.

| Method   | Endpoint                                                                           | Description     |
| :------- | :--------------------------------------------------------------------------------- | :-------------- |
| `POST`   | [`/v1/gateway/groups`](/reference/gateway/groups/create-a-group)                   | Create a group  |
| `GET`    | [`/v1/gateway/groups`](/reference/gateway/groups/list-groups)                      | List groups     |
| `GET`    | [`/v1/gateway/groups/{group_id}`](/reference/gateway/groups/get-a-group)           | Get a group     |
| `GET`    | [`/v1/gateway/groups/{group_id}/usage`](/reference/gateway/groups/get-group-usage) | Get group usage |
| `PATCH`  | [`/v1/gateway/groups/{group_id}`](/reference/gateway/groups/update-a-group)        | Update a group  |
| `DELETE` | [`/v1/gateway/groups/{group_id}`](/reference/gateway/groups/delete-a-group)        | Delete a group  |

## API keys

A federated API key is the credential your customers call with, bound to one group whose limits it inherits. Use these routes to mint, list, and revoke keys.

| Method   | Endpoint                                                                                                   | Description               |
| :------- | :--------------------------------------------------------------------------------------------------------- | :------------------------ |
| `POST`   | [`/v1/gateway/groups/{group_id}/api_keys`](/reference/gateway/api-keys/create-an-api-key)                  | Create an API key         |
| `POST`   | [`/v1/gateway/groups/{group_id}/api_keys/register`](/reference/gateway/api-keys/register-an-api-key)       | Register an API key       |
| `GET`    | [`/v1/gateway/groups/{group_id}/api_keys`](/reference/gateway/api-keys/list-api-keys-for-a-group)          | List API keys for a group |
| `GET`    | [`/v1/gateway/groups/{group_id}/api_keys/{api_key_prefix}`](/reference/gateway/api-keys/get-an-api-key)    | Get an API key            |
| `DELETE` | [`/v1/gateway/groups/{group_id}/api_keys/{api_key_prefix}`](/reference/gateway/api-keys/revoke-an-api-key) | Revoke an API key         |

## Billing webhooks

Frontier Gateway emits a signed per-request usage event to your webhook endpoint for every call. For the payload shape and signature verification, see [Billing webhooks](/reference/gateway/billing-webhooks).
