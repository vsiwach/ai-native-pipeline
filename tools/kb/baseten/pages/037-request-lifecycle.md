# Request lifecycle
Source: https://docs.baseten.co/deployment/autoscaling/request-lifecycle

What happens to a request from submission to response, including routing, queuing, the 1200-second sync predict timeout, and error handling.

When you send an inference request, it doesn't go straight to model code. Whether you use [Model APIs](/inference/model-apis/overview), an OpenAI-compatible endpoint for a deployment you manage, or the [predict API](/inference/calling-your-model), the request passes through authentication, routing, and replica selection first. For Truss deployments with custom model code, your `predict` function runs only after those steps. These layers exist so that Baseten can manage replicas on your behalf: scaling them up when traffic spikes, scaling them down when it drops, and distributing requests across them without any load-balancing code on your side. Understanding what each layer does helps you reason about latency, interpret status codes, and debug production issues.

## How a request reaches your model

Your request first hits Baseten's inference gateway, which authenticates it against your [API key](/organization/api-keys). If authentication fails, the gateway returns a `401 Unauthorized` before the request reaches any model infrastructure.

Once authenticated, the request moves to the routing layer, which decides which replica should handle it. Baseten routes requests to the least-utilized replica based on how full each one is relative to its [concurrency target](/deployment/autoscaling/overview#concurrency-target). Rather than spreading requests evenly across all replicas, the router prefers replicas that already have headroom, which keeps the total number of active replicas low. This matters because you're [billed per minute](/organization/billing) for each running replica.

When the router finds a replica with available capacity, it forwards the request. The replica runs inference. For deployments that use the predict API, your `predict` function executes here. The response flows back through the same path to the client. For most requests, the routing overhead is negligible compared to your model's inference time. The sections below cover what happens when this straightforward path breaks down: when no replica is available, when replicas are overloaded, and when requests fail partway through.

## What happens when no replica is available

If your deployment has scaled to zero, or all existing replicas are at capacity and the autoscaler is still bringing up new ones, incoming requests have nowhere to go. Rather than rejecting them immediately, Baseten parks the request at the routing layer and waits for a replica to become available. Once one is ready, the parked request is forwarded and processed normally. From the client's perspective, the response simply takes longer: the wait time is added on top of the normal inference time.

This parking behavior is what makes [scale-to-zero](/deployment/autoscaling/overview#min_replica) practical. You don't need to build retry logic into your client just because your deployment was idle; the request waits for you. But the wait isn't indefinite. If no replica becomes available before the predict timeout (600 seconds by default) expires, the parked request fails with a `500`. For large models that take several minutes to load weights, you may want to keep [minimum replicas](/deployment/autoscaling/overview#min_replica) above zero so requests always have somewhere to go.

[Async requests](/inference/async) follow a different pattern. The first async request parks and waits, just like a sync request. But subsequent async requests that arrive while there's still no capacity receive an immediate `429` with a `CAPACITY_EXCEEDED` error instead of the `202 Accepted` they'd normally get. This prevents a situation where your client thinks a request was accepted and starts polling for results, when it's actually still waiting for a replica to start.

For strategies to reduce cold start latency, including warm replicas, pre-warming, and the Baseten Delivery Network, see [Cold starts](/deployment/autoscaling/cold-starts).

## Request queuing and load shedding

Even when replicas are running, they can fill up. When all replicas are at their [concurrency target](/deployment/autoscaling/overview#concurrency-target) and the autoscaler hasn't yet finished adding new ones, incoming requests queue at the routing layer. This queuing is automatic: you don't configure it and your client doesn't see it. The request simply waits until a slot opens up on a replica.

Baseten has a **load shedding** safety valve that rejects new requests with a `429` if queued payloads exceed a memory threshold, but this threshold is high enough that it rarely triggers under normal conditions. The more likely issue you'll encounter is requests waiting a long time during traffic spikes, not requests being rejected. Because your client has no visibility into the queue, a request that's waiting for capacity looks the same as a request that's taking a long time to run inference. If you don't want requests to hang indefinitely in this situation, set a client-side timeout so your application can fail fast and either retry or surface an error to the user.

To reduce queuing overall, increase your [max replicas](/deployment/autoscaling/overview#max_replica) so the autoscaler can add capacity faster. Adjusting your [concurrency target](/deployment/autoscaling/overview#concurrency-target) also helps, since a higher target means each replica absorbs more requests before the queue starts filling.

## Internal retries

When a request reaches a replica but the replica returns a `502`, `503`, or `504`, the routing layer doesn't surface the error to your client immediately. Instead, it retries the request automatically using exponential backoff, starting at 500 milliseconds and growing by a factor of 1.5 up to 60 seconds between attempts. For status code errors like these, retries continue until the request deadline or 15 minutes of total elapsed time, whichever comes first. Connection-level failures, where the replica is completely unreachable, are capped at 16 attempts instead. [Async requests](/inference/async) are not retried.

From your client's perspective, retries show up as added latency rather than errors. A request that would have failed on the first attempt may succeed on the second or third, but take noticeably longer than usual. If you're investigating occasional latency spikes where requests take much longer than expected but eventually succeed, you can check the `X-BASETEN-MODEL-PREDICTION-ATTEMPTS` response header: a value greater than 1 confirms that at least one retry happened. Under memory pressure (above 80% utilization on the routing layer), a circuit breaker disables retries entirely to protect stability, resuming them after a 30-second cooldown once memory drops. If a request was pinned to a specific replica through sticky session and that replica returns a `503`, the retry routes to a different replica rather than trying the same one again.

## Timeouts

The **predict timeout** controls how long a sync request can take from the moment it's forwarded to a replica until a response must be returned. If your model's inference exceeds this window, the request is cancelled and the client receives a `504`. The server-side default is 600 seconds (10 minutes). If you need requests to fail faster than that, set a client-side timeout in your HTTP client.

The **async predict timeout** works the same way for [async requests](/inference/async), except that instead of returning a `504` to the caller, the request is marked as failed with a `MODEL_PREDICT_TIMEOUT` error status and your webhook receives the error payload.

The **parking timeout**, which governs how long a request waits in the queue when no replica is available, is set equal to the predict timeout. The logic behind this is that if a request wouldn't have time to complete inference even if a replica appeared right now, there's no benefit to holding it in the queue any longer. One practical consequence is that the predict timeout also determines how long your deployment can take to cold-start before parked requests begin failing.

For **streaming responses**, timeouts behave differently because the HTTP headers, including the `200` status code, are sent when the stream begins. If the timeout expires mid-stream, the stream stops and the connection closes without an error code, since the status was already written. Most HTTP clients surface this as a connection reset or incomplete response rather than a timeout error.

## HTTP status codes

The inference API returns a specific set of status codes, and the sections above explain the conditions that produce each one. This table is a reference for quick lookup.

<Note>
  For what each error means, how to tell a model failure from a Baseten-side issue, and where to look next, see [Inference errors](/inference/errors).
</Note>

| Code  | Meaning               | When it occurs                                                                                                                                       | What to do                                                                                                                                                                                          |
| ----- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `200` | Success               | Normal predict response.                                                                                                                             | None.                                                                                                                                                                                               |
| `202` | Accepted              | Async predict request queued successfully.                                                                                                           | Poll for results or wait for your [webhook](/inference/async).                                                                                                                                      |
| `401` | Unauthorized          | Invalid or missing API key.                                                                                                                          | Check your [API key](/organization/api-keys).                                                                                                                                                       |
| `429` | Too Many Requests     | Load shedding triggered, capacity was unavailable when the request arrived, or a subsequent async request arrived while there was still no capacity. | Retry with exponential backoff. If persistent, increase [max replicas](/deployment/autoscaling/overview#max_replica) or [concurrency target](/deployment/autoscaling/overview#concurrency-target).  |
| `499` | Client Closed Request | Client disconnected before the response was written.                                                                                                 | No server-side action needed. Review client-side timeout configuration if unexpected.                                                                                                               |
| `500` | Internal Server Error | A sync request's parking timeout expired before a replica became available.                                                                          | Retry after a brief wait. If persistent, increase [max replicas](/deployment/autoscaling/overview#max_replica) or keep [minimum replicas](/deployment/autoscaling/overview#min_replica) above zero. |
| `502` | Bad Gateway           | The request was cancelled, or the model became unavailable during inference.                                                                         | Retry. If persistent, check model logs for crashes or errors in your `predict` function.                                                                                                            |
| `503` | Service Unavailable   | The routing layer couldn't find a replica endpoint, typically during a deployment rollout or immediately after a replica failure.                    | Retry. If persistent, check deployment status in the Baseten dashboard.                                                                                                                             |
| `504` | Gateway Timeout       | The request exceeded the server-side predict timeout (1200 seconds).                                                                                 | Optimize your model's inference speed. If you're seeing this consistently, contact support about adjusting the timeout.                                                                             |

<Note>
  A `500` from a sync request during a cold start can mean the parking timeout expired before a replica finished starting. Retrying after a brief wait of 30 seconds to a minute often succeeds once the replica is ready.
</Note>

## Request cancellation

When a client disconnects before the response is written, the routing layer detects the closed connection and cancels the in-flight work. The server logs this as a `499`. In the common case, such as a user closing a browser tab or a client-side timeout firing, this is harmless and the `499` is informational rather than an error.

The more important question is whether cancellation propagates all the way to the GPU. If a client disconnects during a long generation and the model keeps running, you're paying for GPU time that produces tokens nobody will read. Baseten cancels in-flight work automatically so this doesn't happen. When the routing layer detects a disconnect, it signals the inference engine, which aborts the running request and frees GPU resources. This works across engines including TRT-LLM and vLLM.

If you're using a custom model server, you can implement cancellation yourself using Truss request objects. See [Request handling](/development/model/streaming-and-endpoints#request-handling) for code examples.

## Next steps

<CardGroup>
  <Card title="Cold starts" href="/deployment/autoscaling/cold-starts">
    Reduce cold start latency with warm replicas and pre-warming strategies.
  </Card>

  <Card title="Autoscaling" href="/deployment/autoscaling/overview">
    Configure concurrency targets, replica counts, and scaling dynamics.
  </Card>

  <Card title="Async inference" href="/inference/async">
    Fire-and-forget inference with webhook delivery.
  </Card>

  <Card title="Troubleshooting" href="/troubleshooting/deployments">
    Diagnose common deployment issues including autoscaling problems.
  </Card>
</CardGroup>
