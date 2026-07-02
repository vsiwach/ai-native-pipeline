# Cancel a queued async request.
Source: https://docs.baseten.co/api-reference/cancel-a-queued-async-request

/reference/inference-api/inference-api-spec.json delete /async_request/{request_id}
Cancels an async request. Only requests with `QUEUED` status may be canceled. Rate limited to 20 requests per second.
