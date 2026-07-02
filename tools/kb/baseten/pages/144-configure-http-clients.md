# Configure HTTP clients
Source: https://docs.baseten.co/inference/http-client-configuration

Configure connection pooling, retries, and timeouts for reliable inference requests at scale.

When calling Baseten at scale, HTTP client configuration directly affects reliability and throughput.
Misconfigured clients cause `Connection refused` and `Client closed connection` errors that look like platform issues but originate client-side.
To tell a client-side error from a Baseten or model error, see [Inference errors](/inference/errors#is-it-my-model-or-baseten).

<Tip>
  For a drop-in solution, use the [Performance Client](/inference/performance-client), which handles connection pooling, retries, and concurrency automatically.
</Tip>

## Reuse client sessions

Creating a new HTTP client per request is the most common misconfiguration. Each
new client opens a fresh TCP connection, performs a full TLS handshake, and then
discards the connection after a single use. Under load, this pattern quickly
exhausts available ports and produces `Connection refused` errors that appear
intermittent and difficult to diagnose.

A reused client maintains a pool of open connections that are ready for
subsequent requests. This eliminates per-request connection overhead and keeps
your throughput stable as concurrency increases.

<Tabs>
  <Tab title="Recommended">
    Create a single client session and reuse it for all requests:

    ```python predict.py theme={"system"}
    # Correct: reuse a client session
    client = httpx.Client(
        base_url=f"https://model-{model_id}.api.baseten.co",
        headers={"Authorization": f"Bearer {api_key}"},
    )


    def predict(payload):
        response = client.post("/environments/production/predict", json=payload)
        return response.json()
    ```
  </Tab>

  <Tab title="Anti-pattern">
    Creating a new client session for each request opens a fresh TCP connection every time:

    ```python predict.py theme={"system"}
    # Anti-pattern: new client per request
    def predict(payload):
        response = httpx.post(
            url, json=payload, headers=headers
        )  # New connection every time
        return response.json()
    ```
  </Tab>
</Tabs>

## Choose an HTTP client

Your choice of HTTP client library determines which connection management
features are available to you. The [httpx](https://www.python-httpx.org/)
library is recommended over
[requests](https://requests.readthedocs.io/en/latest/) for Baseten workloads
because it provides built-in connection pooling, native async support, and
optional HTTP/2. The `requests` library can achieve connection reuse through its
[`Session`](https://requests.readthedocs.io/en/latest/user/advanced/#session-objects) object, but lacks async support and requires more manual
configuration.

The OpenAI Python SDK uses httpx internally, so if you're already using it, you
benefit from httpx's connection handling by default.

Create a basic [`httpx.Client`](https://www.python-httpx.org/api/#client):

```python client.py theme={"system"}
import httpx

client = httpx.Client(
    base_url=f"https://model-{model_id}.api.baseten.co",
    headers={"Authorization": f"Bearer {api_key}"},
)
```

## Configure connection pooling

Connection pooling keeps a set of open TCP connections ready for reuse. When
your client sends a request, it draws from this pool instead of opening a new
connection. This avoids the cost of repeated TCP handshakes and TLS
negotiations, which can add 50-100ms of latency per request.

The default httpx pool limits (100 total connections, 20 per host) work for
moderate workloads, but high-throughput applications that send hundreds of
concurrent requests will exhaust these limits. When the pool is full, new
requests block until a connection becomes available, resulting in [`PoolTimeout`](https://www.python-httpx.org/exceptions/#pooltimeout)
errors or increased latency.

Increase the pool limits based on your peak concurrency using [`httpx.Limits`](https://www.python-httpx.org/advanced/resource-limits/). The
`max_keepalive_connections` setting controls how many idle connections stay
open, and `keepalive_expiry` controls how long idle connections persist before
closing. Baseten keeps connections alive for 60-120 seconds, so setting
your client's expiry below the server minimum avoids hitting dead connections. Set the limits when you create the client:

```python client.py theme={"system"}
import httpx

limits = httpx.Limits(
    max_connections=256,
    max_keepalive_connections=128,
    keepalive_expiry=30,
)

client = httpx.Client(
    base_url=f"https://model-{model_id}.api.baseten.co",
    headers={"Authorization": f"Bearer {api_key}"},
    limits=limits,
)
```

### Recommended values

| Setting                   | Default (httpx) | Recommended |
| ------------------------- | --------------- | ----------- |
| Max connections           | 100             | 256         |
| Max keepalive connections | 20              | 128         |
| Keep-alive idle timeout   | 5s              | 30s         |
| Keep-alives               | Enabled         | Enabled     |

<Note>
  These values apply when calling a single Baseten model endpoint.
  If you call multiple models, increase max connections proportionally.
</Note>

Keep-alives are always enabled on Baseten.

## Set timeouts

httpx applies a default 5-second timeout to all operations, which is too short
for most inference workloads. LLM generation, image processing, and other model
inference tasks routinely take tens of seconds to minutes. Without properly
configured timeouts, your client will close connections before the model
finishes processing.

Set client timeouts based on your model's expected response time. Baseten's
ingress proxy allows up to 20 minutes (1200 seconds) for synchronous predict
requests, but your client-side timeouts should reflect your actual workload
rather than matching the server maximum.

httpx lets you configure four separate timeout values with [`httpx.Timeout`](https://www.python-httpx.org/advanced/timeouts/). Separating connect and
read timeouts prevents slow network conditions from being confused with slow
model responses. Configure the timeouts when you create the client:

```python client.py theme={"system"}
import httpx

timeout = httpx.Timeout(
    connect=10.0,  # Time to establish connection
    read=1200.0,  # Time to receive response
    write=30.0,  # Time to send request body
    pool=10.0,  # Time to acquire a connection from the pool
)

client = httpx.Client(
    base_url=f"https://model-{model_id}.api.baseten.co",
    headers={"Authorization": f"Bearer {api_key}"},
    timeout=timeout,
)
```

### Timeout guidance by use case

| Use case                 | Connect | Read  | Notes                     |
| ------------------------ | ------- | ----- | ------------------------- |
| LLM inference (sync)     | 10s     | 1200s | Long generation times     |
| Embedding/classification | 10s     | 60s   | Faster response           |
| Async predict (submit)   | 10s     | 30s   | Just submitting the job   |
| Streaming                | 10s     | 1200s | Keep open for full stream |

For long-running requests that exceed sync timeouts, use [async inference](/inference/async) with polling.

## Implement retries

Transient errors happen at scale and can negatively impact your application's reliability and throughput.
Retry with exponential backoff using libraries like [tenacity](https://tenacity.readthedocs.io/en/stable/).

Only retry on transient errors. Retrying client errors like 400 or 401 wastes
time and can mask bugs in your request payload.

Retry on these status codes and connection errors:

* **429** (rate limited)
* **500** (internal server error)
* **502** (bad gateway)
* **503** (service unavailable)
* **504** (gateway timeout)
* Connection errors ([`ConnectError`](https://www.python-httpx.org/exceptions/), `ReadTimeout`)

Don't retry on these status codes:

* **400** (bad request)
* **401** (unauthorized)
* **403** (forbidden)
* **404** (not found)
* **422** (validation error)

The following example uses httpx with tenacity to retry failed requests with exponential backoff:

```python predict.py theme={"system"}
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception


def is_retryable(exception):
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code in (429, 500, 502, 503, 504)
    return isinstance(exception, (httpx.ConnectError, httpx.ReadTimeout))


@retry(
    retry=retry_if_exception(is_retryable),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    stop=stop_after_attempt(5),
)
def predict(client, payload):
    response = client.post("/environments/production/predict", json=payload)
    response.raise_for_status()
    return response.json()
```

## Handle errors

Many errors that look like platform outages actually originate from client-side
misconfiguration. Before opening a support ticket, check whether your error
matches one of these common patterns. If you see `PoolTimeout` or
`Connection refused` under high concurrency, the issue is almost always your
client's pool configuration, not Baseten's servers.

| Error                | Likely cause                        | Resolution                               |
| -------------------- | ----------------------------------- | ---------------------------------------- |
| `PoolTimeout`        | Connection pool exhausted           | Increase pool size or reduce concurrency |
| `ConnectTimeout`     | Network issue or server unavailable | Check network, then retry                |
| `ReadTimeout`        | Model taking longer than expected   | Increase read timeout for your use case  |
| `Connection refused` | Client-side port or pool exhaustion | Increase pool limits, check NAT config   |

## Monitor connections

Connection problems tend to surface as intermittent failures rather than
complete outages, making them difficult to diagnose without proper monitoring. A
gradually exhausting connection pool won't cause errors until it's completely
full, at which point requests start failing unpredictably.

Watch for these signals:

* **Rising p99 latency** without changes to model performance, which often indicates pool contention.
* **Sporadic `Connection refused` errors** under load, which point to port or pool exhaustion.
* **TCP retransmits** increasing over time, which suggest connections are being dropped and recreated.

<Warning>
  If you route traffic through a NAT gateway, monitor port utilization.
  Each outbound connection consumes a port, and high-concurrency workloads can exhaust the available port range, causing intermittent connection failures that are difficult to distinguish from server-side issues.
</Warning>

## Use with proxies

Enterprise deployments often route traffic through HTTP proxies for security, logging, or network policy enforcement. httpx supports proxy configuration at the client level, so connection pooling and keep-alives continue to work through the proxy.

You may need to increase your pool limits when using a proxy, since the additional network hop increases per-request latency, which means connections are held open longer and the pool drains faster under the same concurrency. Pass the proxy URL when you create the client:

```python client.py theme={"system"}
import httpx

client = httpx.Client(
    base_url=f"https://model-{model_id}.api.baseten.co",
    headers={"Authorization": f"Bearer {api_key}"},
    proxy="http://corporate-proxy.example.com:8080",
    limits=httpx.Limits(max_connections=300),
)
```

## Further reading

* [Performance Client](/inference/performance-client): Handles connection pooling, retries, and concurrency automatically.
* [Async inference](/inference/async): For long-running requests that exceed sync timeout limits.
* [Streaming](/inference/streaming): For streaming model responses.
