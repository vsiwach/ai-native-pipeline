# Async inference
Source: https://docs.baseten.co/inference/async

Run asynchronous inference on deployed models

Async inference is a *fire and forget* pattern for model requests. Instead of
waiting for a response, you receive a request ID immediately while inference
runs in the background. When complete, results are delivered to your webhook
endpoint.

<Note>
  Async requests work with any deployed model. You don't need code changes.
  Requests can queue for up to 72 hours and run for up to 1 hour. Async inference is not
  compatible with streaming output.
</Note>

Use async inference for:

* **Long-running tasks** that would otherwise hit request timeouts.
* **Batch processing** where you don't need immediate responses.
* **Priority queuing** to serve VIP customers faster.

<Warning>
  Baseten does not store model outputs. If webhook delivery fails after all retries,
  your data is lost. See [Webhook delivery](#webhook-delivery) for mitigation
  strategies.
</Warning>

## Quick start

<Steps>
  <Step title="Set up a webhook endpoint">
    Create an HTTPS endpoint to receive results. Deploy to any service that can receive POST requests.
  </Step>

  <Step title="Make an async request">
    Call your model's `/async_predict` endpoint with your webhook URL:

    ```python theme={"system"}
    import requests
    import os

    model_id = "YOUR_MODEL_ID"
    webhook_endpoint = "YOUR_WEBHOOK_ENDPOINT"
    baseten_api_key = os.environ["BASETEN_API_KEY"]

    # Call the async_predict endpoint of the production deployment
    resp = requests.post(
        f"https://model-{model_id}.api.baseten.co/production/async_predict",
        headers={"Authorization": f"Bearer {baseten_api_key}"},
        json={
            "model_input": {"prompt": "hello world!"},
            "webhook_endpoint": webhook_endpoint,
            # "priority": 0,
            # "max_time_in_queue_seconds": 600,
        },
    )

    print(resp.json())
    ```

    You'll receive a `request_id` immediately.
  </Step>

  <Step title="Receive results">
    When inference completes, Baseten sends a POST request to your webhook with the model output.
    See [Webhook payload](#webhook-payload) for the response format.
  </Step>
</Steps>

<Tip>
  **Chains** support async inference through `async_run_remote`.
  Inference requests to the entrypoint are queued, but internal Chainlet-to-Chainlet calls run synchronously.
</Tip>

## How async works

Async inference decouples request submission from processing, letting you queue work without waiting for results.

### Request lifecycle

When you submit an async request:

1. You call `/async_predict` and immediately receive a `request_id`.
2. Your request enters a queue managed by the Async Request Service.
3. A background worker picks up your request and calls your model's predict endpoint.
4. Your model runs inference and returns a response.
5. Baseten sends the response to your webhook URL using POST.

The `max_time_in_queue_seconds` parameter controls how long a request waits
before expiring. It defaults to 10 minutes but can extend to 72 hours.

### Autoscaling behavior

The async queue is decoupled from model scaling. Requests queue successfully
even when your model has zero replicas.

When your model is scaled to zero:

1. Your request enters the queue while the model has no running replicas.
2. The queue processor attempts to call your model, triggering the autoscaler.
3. Your request waits while the model cold-starts.
4. Once the model is ready, inference runs and completes.
5. Baseten delivers the result to your webhook.

If the model doesn't become ready within `max_time_in_queue_seconds`, the
request expires with status `EXPIRED`. Set this parameter to account for your
model's startup time. For models with long cold starts, consider keeping minimum
replicas running using
[autoscaling settings](/deployment/autoscaling/overview).

### Async priority

Async requests are subject to two levels of priority: how they compete with sync
requests for model capacity, and how they're ordered relative to other async
requests in the queue.

#### Sync vs async concurrency

Sync and async requests share your model's concurrency pool, controlled by
`predict_concurrency` in your model configuration:

```yaml config.yaml theme={"system"}
runtime:
  predict_concurrency: 10
```

The `predict_concurrency` setting defines how many requests your model can
process simultaneously per replica. When both sync and async requests are in
flight, sync requests take priority. The queue processor monitors your model's
capacity and backs off when it receives 429 responses, ensuring sync traffic
isn't starved.

For example, if your model has `predict_concurrency=10` and 8 sync requests are
running, only 2 slots remain for async requests. The remaining async requests
stay queued until capacity frees up.

#### Async queue priority

Within the async queue itself, you can control processing order using the
`priority` parameter. This is useful for serving specific requests faster or
ensuring critical batch jobs run before lower-priority work. Set the `priority` field when you submit the request:

```python async_predict.py theme={"system"}
import requests
import os

model_id = "YOUR_MODEL_ID"
webhook_endpoint = "YOUR_WEBHOOK_URL"
baseten_api_key = os.environ["BASETEN_API_KEY"]

resp = requests.post(
    f"https://model-{model_id}.api.baseten.co/production/async_predict",
    headers={"Authorization": f"Bearer {baseten_api_key}"},
    json={
        "webhook_endpoint": webhook_endpoint,
        "model_input": {"prompt": "hello world!"},
        "priority": 0,
    },
)

print(resp.json())
```

The `priority` parameter accepts values 0, 1, or 2. Lower values indicate higher
priority: a request with `priority: 0` is processed before requests with
`priority: 1` or `priority: 2`. If you don't specify a priority, requests
default to priority 0.

Because unspecified requests default to priority 0, use the `priority` parameter
mainly to *demote* less urgent work: set background or batch jobs to `priority: 1`
or `priority: 2` so they yield to default-priority traffic. Marking every request
with the same priority has no effect on ordering.

### Watch the queue

Two things decide how quickly an async request clears: its `priority` against the
other requests in the queue, and how it competes with sync traffic for replica
capacity. The simulation below shows both. Requests pile up in the async queue, a
load balancer pulls the front of the queue and sends each request to a free replica,
and the replica runs it and frees up for the next.

<AsyncQueue />

Requests arrive at the back of the queue and cut ahead of every lower-priority
request, so a `priority` 0 jumps to the front. The load balancer clears the queue as
fast as it can, always dispatching the front request, so higher-priority work reaches
a replica first. The figure shows each replica handling one request at a time. Switch
to **Sync contention** to add sync traffic: sync and async share replica capacity, and
sync takes precedence. Sync requests go straight to the replicas, so when sync surges
the load balancer cannot place async work and backs off when it hits a `429`. As the
surge recedes, the load balancer drains the backlog across the freed replicas.

## Webhooks

Baseten delivers async results to your webhook endpoint when inference completes.

### Request format

When inference completes, Baseten sends a POST request to your webhook with these headers and body:

```text HTTP request theme={"system"}
POST /your-webhook-path HTTP/2.0
Content-Type: application/json
X-BASETEN-REQUEST-ID: 9876543210abcdef1234567890fedcba
X-BASETEN-SIGNATURE: v1=abc123...
```

The `X-BASETEN-REQUEST-ID` header contains the request ID for correlating webhooks with your original requests.
The `X-BASETEN-SIGNATURE` header is only included if a [webhook secret](#secure-webhooks) is configured.

<Note>
  Webhook endpoints must use HTTPS (except `localhost` for development). Baseten
  supports HTTP/2 and HTTP/1.1 connections.
</Note>

The body is a JSON object like this:

```json Webhook payload theme={"system"}
{
  "request_id": "9876543210abcdef1234567890fedcba",
  "model_id": "abc123",
  "deployment_id": "def456",
  "type": "async_request_completed",
  "time": "2024-04-30T01:01:08.883423Z",
  "data": { "output": "model response here" },
  "errors": []
}
```

The body contains the `request_id` matching your original `/async_predict`
response, along with `model_id` and `deployment_id` identifying which deployment
ran the request. The `data` field contains your model output, or `null` if an
error occurred. The `errors` array is empty on success, or contains error
objects on failure. For what each status code means and how to respond, see [Inference errors](/inference/errors).

### Webhook delivery

<Warning>
  If all delivery attempts fail, your model output is permanently lost.
</Warning>

Baseten delivers webhooks on a best-effort basis with automatic retries:

| Setting         | Value                             |
| --------------- | --------------------------------- |
| Total attempts  | 2 (1 initial + 1 retry).          |
| Backoff         | About 2 seconds before the retry. |
| Timeout         | 10 seconds per attempt.           |
| Retryable codes | 500, 502, 503, 504.               |

**To prevent data loss:**

1. **Save outputs in your model.** Use the `postprocess()` function to write to
   cloud storage:

```python model/model.py theme={"system"}
import json
import boto3

class Model:
  # ...
    def postprocess(self, model_output):
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket="my-bucket",
            Key=f"outputs/{self.context.get('request_id')}.json",
            Body=json.dumps(model_output)
        )
        return model_output
```

The `postprocess` method runs after inference completes. Use
`self.context.get('request_id')` to access the async request ID for correlating
outputs with requests.

2. **Use a reliable endpoint.** Deploy your webhook to a highly available
   service like a cloud function or message queue.

### Secure webhooks

Create a webhook secret in the
[Secrets tab](https://app.baseten.co/settings/secrets) to verify requests are
from Baseten.

When configured, Baseten includes an `X-BASETEN-SIGNATURE` header:

```text HTTP header theme={"system"}
X-BASETEN-SIGNATURE: v1=abc123...
```

To validate, compute an HMAC-SHA256 of the request body using your secret and compare:

```python verify_signature.py theme={"system"}
import hashlib
import hmac

def verify_signature(body: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    actual = signature.replace("v1=", "").split(",")[0]
    return hmac.compare_digest(expected, actual)
```

The function computes an HMAC-SHA256 hash of the raw request body using your
webhook secret. It extracts the signature value after `v1=` and uses
`compare_digest` for timing-safe comparison to prevent timing attacks.

Rotate secrets periodically. During rotation, both old and new secrets remain
valid for 24 hours.

## Manage requests

You can check the status of async requests or cancel them while they're queued.

### Check request status

To check the status of an async request, call the status endpoint with your request ID:

```python theme={"system"}
import requests
import os

model_id = "YOUR_MODEL_ID"
request_id = "YOUR_REQUEST_ID"
baseten_api_key = os.environ["BASETEN_API_KEY"]

resp = requests.get(
    f"https://model-{model_id}.api.baseten.co/async_request/{request_id}",
    headers={"Authorization": f"Bearer {baseten_api_key}"}
)

print(resp.json())
```

Status is available for 1 hour after completion. See the
[status API reference](/reference/inference-api/status-endpoints/get-async-request-status)
for details.

The status and cancel endpoints take a model ID and a `request_id` only — there's no environment segment in the path. A `request_id` is globally unique, so you don't need to know which environment or deployment originally accepted the request to look it up.

| Status           | Description                                      |
| ---------------- | ------------------------------------------------ |
| `QUEUED`         | Waiting in queue.                                |
| `IN_PROGRESS`    | Currently processing.                            |
| `SUCCEEDED`      | Completed successfully.                          |
| `FAILED`         | Failed after retries.                            |
| `EXPIRED`        | Exceeded `max_time_in_queue_seconds`.            |
| `CANCELED`       | Canceled by user.                                |
| `WEBHOOK_FAILED` | Inference succeeded but webhook delivery failed. |

### Cancel a request

Only `QUEUED` requests can be canceled. Once a request enters `IN_PROGRESS`, the cancel endpoint can't stop it — the request runs to completion (or fails). If you need to bound how long a request can wait before running, set [`max_time_in_queue_seconds`](#request-lifecycle) on the request so stale requests transition to `EXPIRED` instead of executing.

To cancel a queued request, call the cancel endpoint with your request ID:

```python cancel_request.py theme={"system"}
import requests
import os

model_id = "YOUR_MODEL_ID"
request_id = "YOUR_REQUEST_ID"
baseten_api_key = os.environ["BASETEN_API_KEY"]

resp = requests.delete(
    f"https://model-{model_id}.api.baseten.co/async_request/{request_id}",
    headers={"Authorization": f"Bearer {baseten_api_key}"}
)

print(resp.json())
```

For more information, see the [cancel async request API reference](/reference/inference-api/predict-endpoints/cancel-async-request).

## Error codes

When inference fails, the webhook payload returns an `errors` array:

```json Webhook payload theme={"system"}
{
  "errors": [{ "code": "MODEL_PREDICT_ERROR", "message": "Details here" }]
}
```

| Code                    | HTTP    | Description                      | Retried |
| ----------------------- | ------- | -------------------------------- | ------- |
| `MODEL_NOT_READY`       | 400     | Model is loading or starting.    | Yes     |
| `MODEL_DOES_NOT_EXIST`  | 404     | Model or deployment not found.   | No      |
| `MODEL_INVALID_INPUT`   | 422     | Invalid input format.            | No      |
| `MODEL_PREDICT_ERROR`   | 500     | Exception in `model.predict()`.  | Yes     |
| `MODEL_UNAVAILABLE`     | 502/503 | Model crashed or scaling.        | Yes     |
| `MODEL_PREDICT_TIMEOUT` | 504     | Inference exceeded timeout.      | Yes     |
| `INTERNAL_SERVER_ERROR` | N/A     | Something went wrong on Baseten. | Yes     |

### Inference retries

When inference fails with a retryable error, Baseten automatically retries the
request using exponential backoff. Configure this behavior with
`inference_retry_config`:

```python async_predict.py theme={"system"}
import requests
import os

model_id = "YOUR_MODEL_ID"
webhook_endpoint = "YOUR_WEBHOOK_URL"
baseten_api_key = os.environ["BASETEN_API_KEY"]

resp = requests.post(
    f"https://model-{model_id}.api.baseten.co/production/async_predict",
    headers={"Authorization": f"Bearer {baseten_api_key}"},
    json={
        "model_input": {"prompt": "hello world!"},
        "webhook_endpoint": webhook_endpoint,
        "inference_retry_config": {
            "max_attempts": 3,
            "initial_delay_ms": 1000,
            "max_delay_ms": 5000
        }
    },
)

print(resp.json())
```

| Parameter          | Range    | Default | Description                                      |
| ------------------ | -------- | ------- | ------------------------------------------------ |
| `max_attempts`     | 1-10     | 3       | Total inference attempts including the original. |
| `initial_delay_ms` | 0-10,000 | 1000    | Delay before the first retry (ms).               |
| `max_delay_ms`     | 0-60,000 | 5000    | Maximum delay between retries (ms).              |

Retries use exponential backoff with a multiplier of 2. With the default
configuration, delays progress as: 1s → 2s → 4s → 5s (capped at `max_delay_ms`).

Only requests that fail with retryable error codes (500, 502, 503, 504) are
retried. Non-retryable errors like invalid input (422) or model not found (404)
fail immediately.

<Note>
  Inference retries are distinct from [webhook delivery retries](#webhook-delivery).
  Inference retries happen when calling your model fails. Webhook retries happen
  when delivering results to your endpoint fails.
</Note>

## Rate limits

There are rate limits for the async predict endpoint and the status polling endpoint.
If you exceed these limits, you'll receive a 429 status code.

| Endpoint                                     | Limit                               |
| -------------------------------------------- | ----------------------------------- |
| Predict endpoint requests (`/async_predict`) | 12,000 requests/minute (org-level). |
| Status polling                               | 100 requests/second.                |
| Cancel request                               | 100 requests/second.                |

Use webhooks instead of polling to avoid status endpoint limits. Contact
[support@baseten.co](mailto:support@baseten.co) to request increases.

## Observability

Async metrics are available on the
[Metrics tab](/observability/metrics#async-queue-metrics) of your model
dashboard:

* **Inference latency/volume**: includes async requests.
* **Time in async queue**: time spent in `QUEUED` state.
* **Async queue size**: number of queued requests.

<Frame>
  <img />
</Frame>

## Related

<CardGroup>
  <Card title="Webhook secrets" icon="key" href="https://app.baseten.co/settings/secrets">
    Configure webhook secrets in your Baseten settings to secure webhook delivery.
  </Card>
</CardGroup>
