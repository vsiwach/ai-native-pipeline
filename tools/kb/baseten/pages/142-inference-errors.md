# Inference errors
Source: https://docs.baseten.co/inference/errors

What each inference error means and where to look next.

When an inference request fails, the error message alone often isn't enough to tell you what to fix. The status code is the first clue. It tells you the broad category, and because your request passes through Baseten's inference gateway before it reaches your model, it also points at where the failure happened: your request, the Baseten platform, or your model's own code.

Every failed response is JSON, in the form `{"error": "<message>"}`. This page maps each status code to its likely source and the fastest way to confirm it. Start with the [quick reference](#quick-reference), then read the section for the status code you received. Streaming and async requests report failures differently. See [Streaming and async errors](#streaming-and-async-errors).

## How to read an inference error

A failed response has two parts worth reading:

* **The status code**: the broad category, returned in the HTTP response (`502`, `503`, and so on).
* **The error body**: `{"error": "<message>"}`. The message is either a short string Baseten generates (such as `Error making prediction`) or, when your model itself returned the error, the raw response your model produced, passed through unchanged.

One distinction resolves most failures: did your model return the error, or was your model unreachable? See [Is it my model or Baseten?](#is-it-my-model-or-baseten).

## Quick reference

| Status                        | What it usually means                                                            | Where to look                                                                                      |
| ----------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `400` / `401` / `403` / `404` | Malformed request, invalid API key, or wrong model ID                            | Your request: [check the endpoint and API key](#400-401-403-404-request-and-authentication-errors) |
| `402`                         | Billing or payment issue on the account                                          | [Billing and usage](/organization/billing)                                                         |
| `413`                         | Request body too large: 100 MB edge cap (all requests), or 256 KiB async default | Send large inputs by [file or URL](/inference/output-format/files), not inline                     |
| `502`                         | Your container crashed or restarted mid-request, or a Baseten-side error         | [Model logs](/observability/logs) for a crash or `OOMKilled`; if clean, retry                      |
| `503`                         | Container not available yet: draining or routing                                 | Mostly transient: retry with exponential backoff                                                   |
| `504`                         | The prediction exceeded the request timeout (1200s sync)                         | Profile the model, raise resources, or use [async](/inference/async)                               |

## Is it my model or Baseten?

When a request reaches your model and your model server responds with an error, Baseten passes that response through to you. When the request never gets a real answer from your model, Baseten returns its own error instead. Telling these apart is the fastest way to know where to debug.

**Your model returned the error**: the status code and body come from your model server. Your handler raised an exception, returned a non-2xx status, or timed out internally. Debug it like any application bug, starting from the error body and your [model logs](/observability/logs).

**Your model was unreachable**: the request failed in front of your container, so you get a message like `Error making prediction` with a `502` or `503`. The container is down, restarting, was killed (for example, out of memory), or is still cold-starting.

The most common version of the second case is memory pressure. When you increase your payload or batch sizes, each request uses more memory, and the container can be killed mid-request (`OOMKilled`). Confirm it by checking your [model logs](/observability/logs) for `OOMKilled` or repeated restarts, and your [metrics](/observability/metrics) for memory pressure and replica restarts. To fix it, reduce per-request memory with smaller batches or payloads, or move to a larger instance type.

## Errors by status code

Each section below covers what the status code means, its common causes, and what to check first.

### 400, 401, 403, 404: request and authentication errors

These point to the request itself, not your model.

* **`401` / `403`**: the API key is missing or invalid. Use a valid [Baseten API key](/organization/api-keys) in the `Authorization` header.
* **`404`**: the model or deployment ID doesn't exist, or the model was deleted. Confirm the ID and that you're calling the right [predict endpoint](/inference/calling-your-model).
* **`400`**: the request or URL is malformed. Check the request body is valid JSON and the path is correct.

For Truss CLI authentication errors (such as a missing key in `~/.trussrc`), see [Troubleshooting inference](/troubleshooting/inference).

### 402: payment required

The account has an unresolved billing or payment issue, such as exhausted credits with no payment method on file. Check your [billing and usage](/organization/billing) settings, or contact your account owner.

### 413: payload too large

The request body exceeded a size limit. Two limits can return a `413`:

* **Edge limit**: the ingress proxy caps every inbound request body at [100 MB](/reference/inference-api/overview#request-size) and rejects larger requests before they reach your model or chain. It covers the full HTTP body, including the JSON envelope and any base64-encoded media, and isn't configurable.
* **Async limit**: [async requests](/inference/async) have a smaller per-organization cap, 256 KiB (262,144 bytes) by default. The message reports both sizes: `payload size of X bytes exceeds maximum size of Y bytes`.

<Note>
  The async payload limit is set per organization. [Contact support](mailto:support@baseten.co) to raise it for your organization. The 100 MB edge limit is fixed.
</Note>

For large inputs, send a file or URL the model fetches instead of inlining the bytes in the request body. See [Model I/O with files](/inference/output-format/files). A payload that fits under the edge limit but exhausts the container's memory returns a `502`, not a `413`. See [Is it my model or Baseten?](#is-it-my-model-or-baseten).

### 502: bad gateway

A `502` has two meanings, and they need different responses:

* **Your container was unreachable**: the most common case. The container crashed, restarted, or was killed (for example, `OOMKilled`) mid-request. The body is a short message like `Error making prediction`. Check your [model logs](/observability/logs) for a crash or restart. See [Is it my model or Baseten?](#is-it-my-model-or-baseten).
* **A Baseten-side error**: a transient problem in the gateway or routing layer. If your model logs are clean and show no crash, retry with exponential backoff.

You might also see a `502` reported as `client closed connection`. That means the client disconnected before the response finished, not a Baseten or model failure.

### 503: service unavailable

The container isn't available to take the request yet. This is usually transient. Retry with exponential backoff. Common causes:

* **Draining**: an instance is shutting down during a deploy or scale-down. The message asks you to retry on another instance.
* **Routing**: the request couldn't be routed to a workload plane, or a circuit breaker is open to protect an unhealthy upstream.

A request that arrives while the deployment is scaling up from zero doesn't return a `503`. Baseten holds it at the routing layer until a replica is ready, then forwards it. See [Request lifecycle](/deployment/autoscaling/request-lifecycle).

<Note>
  Async requests return `503` rather than `502` when the async service isn't set up on the workload plane yet. See [Async inference](/inference/async).
</Note>

### 504: gateway timeout

The prediction ran longer than the [request timeout](/reference/inference-api/overview#timeouts) (1200 seconds for sync predict). Common causes are a model that's too slow for the payload, an under-provisioned instance, or a hung request. Profile the model, raise its resources, or move long-running work to the [async API](/inference/async), which allows up to 3600 seconds.

If you see a timeout sooner than 1200 seconds, check your client's own timeout. Set it to match your model's expected response time. See [Configure HTTP clients](/inference/http-client-configuration#set-timeouts).

## Streaming and async errors

Not every failure arrives as a status code with a JSON body.

**Streaming responses**: a streaming response starts with a `200` and an open connection, so a failure partway through (a timeout, or the model becoming unavailable) can't be sent as a `5xx` with an error body. The stream ends early instead. If a stream stops before you receive the end of the response, treat it as a failed request: check your [model logs](/observability/logs) and retry.

**Async requests**: a failure isn't reported on the submit response. The submit returns once the request is queued, and any error is reported later in the result payload's `errors` array, which is empty on success. See [Async inference](/inference/async).

## Where to look next

When an error isn't self-explanatory, these are the fastest places to confirm a cause:

* **[Model logs](/observability/logs)**: crashes, restarts, `OOMKilled`, and your model's own error output.
* **[Metrics](/observability/metrics)**: memory pressure, replica count and restarts, and queue depth.
* **[Request lifecycle](/deployment/autoscaling/request-lifecycle)**: how queuing, cold starts, and concurrency affect request handling.
* **[Async inference](/inference/async)**: for payloads or runtimes that shouldn't go through the synchronous path.

If you're still stuck, contact support with your model or deployment ID, the timestamp, the status code, and the request ID.
