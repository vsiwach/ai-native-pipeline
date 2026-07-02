# Errors
Source: https://docs.baseten.co/reference/sdk/loops/errors

The Loops SDK exception types and when each is raised.

Exceptions raised by the [ServiceClient](/reference/sdk/loops/service-client), [TrainingClient](/reference/sdk/loops/training-client), and [SamplingClient](/reference/sdk/loops/sampling-client) when a server operation fails.

<ParamField>
  The server reports that an async operation failed. The `error_class` attribute carries the server-side exception class name (for example, `"ValueError"` or `"DispatcherError"`), which is useful for routing in caller code.
</ParamField>

<ParamField>
  The server returned 404 for an operation ID. This can mean the server has no record of the operation (after a pod restart, for example) or that the result was TTL-evicted. Resubmit the operation if the work is still needed; the server's idempotency-key deduplication prevents double-execution.
</ParamField>

<ParamField>
  The server is shutting down (503 response). Retry the request against a different replica.
</ParamField>
