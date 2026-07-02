# Baseten Frontier Gateway
Source: https://docs.baseten.co/frontier-gateway/overview

A managed API gateway for AI labs to serve hosted models under a branded URL with hierarchical groups, inherited rate and usage limits, and billing webhooks.

You have a model deployed on Baseten and want to give your own customers access through your branded domain, with credentials you control and usage you meter. Baseten Frontier Gateway is the managed API gateway that makes this possible. It adds a hierarchical group resource model, per-group rate and usage limits with inheritance, billing webhooks, and white-label routing on top of your Dedicated deployment, so your customers call your model through your domain with keys you mint and revoke through the Baseten REST API.

<Note>
  To enable Frontier Gateway for your workspace, [talk to us](https://www.baseten.co/talk-to-us/).
</Note>

## How Frontier Gateway works

Frontier Gateway sits on top of an existing Dedicated deployment. You publish **endpoints** to map your routing slugs to deployments, and you model your customers, plans, and projects as a tree of **groups**.

An **endpoint** is a routing slug (for example `my-org/glm-5.2`) and the target it points to. You create, re-point, and delete endpoints yourself through the REST API. For more information, see [Endpoints](/frontier-gateway/endpoints).

Each **group** owns an external identifier (`metadata.external_entity_id`), the set of model slugs it's allowed to call, and the rate and usage limits enforced on every call. Groups can nest under a parent group, and limits flow down the tree according to the group's `limit_enforcement` mode. You then mint one or more API keys under any group; those keys are what your customer uses. Every key inherits the effective config of its group, so rotating credentials never changes what the customer can spend.

When a request hits the gateway with one of your federated keys, Baseten validates the key, walks up the owning group's hierarchy to compute effective limits, and enforces them per model slug. Valid requests route to the deployment the slug's endpoint points to, and the response returns to the caller. For each request, Baseten emits a signed billing event out-of-band to your webhook endpoint with token counts and request metadata, so your billing pipeline runs independently of the inference path.

## Key features

* **Self-service endpoints**: Map a routing slug to a Baseten deployment, re-point it, or retire it through the REST API. For more information, see [Endpoints](/frontier-gateway/endpoints).
* **Hierarchical groups**: Model your organization however your billing structure fits, whether that's orgs and projects, plans and customers, or tenants and seats. Groups carry the model set and the limits; keys hang off groups and inherit them. For more information, see [Manage groups and API keys](/frontier-gateway/api-keys).
* **Two inheritance modes**: Pick an enforcement mode per hierarchy. An independent hierarchy lets children override their parents and meters each group's usage separately; a cascading hierarchy makes a group's usage count against every ancestor at once. For more information, see [Inheritance modes](/frontier-gateway/rate-limits#inheritance-modes).
* **Per-group, per-model rate and usage limits**: Configure `TOKEN` or `REQUEST` limits on each group, scoped per model slug. Every key minted under the group inherits the group's effective limits.
* **Billing webhooks**: Receive signed per-request token usage events you can pipe into Stripe, Orb, or your own billing system. For more information, see [Billing webhooks](/frontier-gateway/billing-webhooks).
* **White-label routing** (coming soon): Serve inference traffic from your branded domain so downstream customers never see the Baseten URL. Contact your onboarding engineer for current availability.

## Frontier Gateway versus Model APIs

Frontier Gateway and Model APIs are distinct products with separate APIs. Frontier Gateway management lives under `/v1/gateway/` and is gated to Frontier Gateway customers; public Model APIs customers authenticate with their workspace API key and call inference at `/v1/chat/completions` directly. Use the table below to confirm which product you need.

|                | Frontier Gateway                                               | Model APIs                                         |
| -------------- | -------------------------------------------------------------- | -------------------------------------------------- |
| Who it's for   | AI labs serving their own hosted model to downstream customers | App developers calling a Baseten-hosted open model |
| Authentication | Federated API keys you mint per group                          | Your workspace API key                             |
| Compute        | Your Dedicated deployment                                      | Shared Baseten infrastructure                      |
| Documentation  | [Frontier Gateway](/frontier-gateway/overview)                 | [Model APIs](/inference/model-apis/overview)       |

## Next steps

* **[Get started](/frontier-gateway/get-started)**: Walk through your first endpoint, group, API key, and inference call.
* **[Endpoints](/frontier-gateway/endpoints)**: Map routing slugs to deployments and manage them through the REST API.
* **[Manage groups and API keys](/frontier-gateway/api-keys)**: Create groups, build a hierarchy, and mint or revoke keys.
* **[Rate and usage limits](/frontier-gateway/rate-limits)**: Control per-group, per-model usage and pick an inheritance mode.
* **[Billing webhooks](/frontier-gateway/billing-webhooks)**: Meter usage by consuming signed per-request events.
