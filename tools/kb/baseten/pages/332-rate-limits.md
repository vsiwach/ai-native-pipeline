# Rate limits
Source: https://docs.baseten.co/reference/management-api/rate-limits

Rate limits, response shape, and retry handling for the Baseten management API.

Baseten enforces per-API-key rate limits on the management API. The limits protect shared infrastructure, such as the build queue, from bursty automation.

## Limits

The default limit applies to every `/v1/*` endpoint. A few endpoints that touch shared build and deployment infrastructure have stricter limits.

| Endpoint                                                            | Limit               |
| ------------------------------------------------------------------- | ------------------- |
| `POST /v1/models/{model_id}/deployments/development/activate`       | 20 requests/minute  |
| `POST /v1/models/{model_id}/deployments/production/activate`        | 20 requests/minute  |
| `POST /v1/models/{model_id}/deployments/{deployment_id}/activate`   | 20 requests/minute  |
| `POST /v1/models/{model_id}/deployments/development/deactivate`     | 20 requests/minute  |
| `POST /v1/models/{model_id}/deployments/production/deactivate`      | 20 requests/minute  |
| `POST /v1/models/{model_id}/deployments/{deployment_id}/deactivate` | 20 requests/minute  |
| `POST /v1/models/{model_id}/deployments/development/retry`          | 10 requests/minute  |
| `POST /v1/models/{model_id}/deployments/production/retry`           | 10 requests/minute  |
| `POST /v1/models/{model_id}/deployments/{deployment_id}/retry`      | 10 requests/minute  |
| `POST /v1/models/{model_id}/deployments/{deployment_id}/logs`       | 30 requests/second  |
| All other `/v1/*` endpoints                                         | 100 requests/second |

Baseten tracks each endpoint separately.

## Rate-limited responses

A request over the limit returns `429 Too Many Requests`:

```json theme={"system"}
{
  "error": "Rate limit exceeded. Please try again later.",
  "retry_after": 37
}
```

`retry_after` is the number of seconds until the current rate-limit window resets. Wait at least that long before retrying.

## Retry handling

For CI pipelines or scripts that call the management API in a loop, handle `429` explicitly:

```python theme={"system"}
import time
import requests

def post_with_retry(url, headers, max_attempts=5):
    for _ in range(max_attempts):
        response = requests.post(url, headers=headers)
        if response.status_code != 429:
            return response
        retry_after = response.json().get("retry_after", 1)
        time.sleep(retry_after)
    return response
```

Back off on `retry_after` instead of retrying immediately. A tight retry loop wastes API calls; the server rejects every request until the window resets.

## Request higher limits

If your workload needs sustained throughput above the default limits, [contact support](https://www.baseten.co/talk-to-us/increase-rate-limits/) to request per-endpoint increases for your organization.
