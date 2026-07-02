# Metrics
Source: https://docs.baseten.co/observability/metrics

Understand the load and performance of your model

The Metrics tab in the model dashboard tracks model load and performance. Use the dropdowns at the top of the tab to scope by environment, deployment, or time range.

Environment scope aggregates metrics across every deployment in that environment, which helps you watch a rollout or compare trends across the whole environment. Deployment scope restricts metrics to a single deployment ID for diagnosing one version in isolation.

<img />

## Customize your view

By default the Metrics tab shows a standard set of graphs. Use the **Customize view** button at the top of the tab to show, hide, and reorder any graph, and your layout is saved per model. A hidden graph stays in the Customize view panel, so you can turn it back on at any time.

## Inference volume

Tracks the request rate over time, segmented by HTTP status codes:

* `2xx`: 🟢 Successful requests
* `4xx`: 🟡 Client errors
* `5xx`: 🔴 Server errors (includes model prediction exceptions)

<Note>
  For non-HTTP models and Chains (WebSockets and gRPC), the status codes reflect the status codes for those protocols. For a full list of the WebSocket close codes surfaced here, see [WebSocket status codes](/development/model/websockets#inference-volume).
</Note>

***

## Response time

Measured at different percentiles (p50, p90, p95, p99):

* **End-to-end response time:** Includes cold starts, queuing, and inference (excludes client-side latency). Reflects real-world performance.
* **Inference time:** Covers only model execution, including pre/post-processing. Useful for optimizing single-replica performance.
* **Time to first byte:** Measures the time-to-first-byte time distribution, including any queueing and routing time. A proxy for TTFT.

***

## Request and response size

Measured at different percentiles (p50, p90, p95, p99):

* **Request size:** Tracks the request size distribution. A proxy for input tokens.
* **Response size:** Tracks the response size distribution. A proxy for generated tokens.

***

## Replicas

Tracks the number of **active** and **starting** replicas:

* **Starting:** Waiting for resources or loading the model.
* **Active:** Ready to serve requests.
* For development deployments, a replica is considered active while running the live reload server.

To see pods split by their Kubernetes Ready condition, for example when a [readiness probe](/development/model/health-checks#readiness-probe) pulls a replica out of traffic, export [`baseten_pod_readiness`](/observability/export-metrics/supported-metrics#baseten_pod_readiness).

***

## Restarts

Tracks the cumulative number of times the model container has been restarted. Restarts are typically caused by application crashes, out-of-memory kills, or failed [liveness probes](/development/model/health-checks#liveness-probe).

Frequent restarts usually indicate one of:

* A crash in `load()` or in your model code.
* An out-of-memory event: check the **Memory usage** graph.
* A liveness probe failing under load: review `restart_threshold_seconds` and any [custom health check logic](/development/model/health-checks#custom-health-check-logic).

***

## Concurrent requests

Total in-flight inference requests across replicas, including both requests currently being serviced and requests waiting to be processed. [Async inference requests](/inference/async) are not included in this metric.

This is the primary signal that drives [autoscaling](/deployment/autoscaling/overview) decisions. For the full metric definition and labels, see [`baseten_concurrent_requests`](/observability/export-metrics/supported-metrics#baseten_concurrent_requests).

This metric is a point-in-time gauge, sampled roughly every 30 seconds, while inference volume counts every request over the full minute. The two relate through Little's Law:

`average concurrency ≈ requests per second × average end-to-end latency`

When requests are fast, that product stays well below 1 even at high volume, so most samples catch the system empty and the gauge reads 0. For example, 600 requests per minute at 80 ms latency averages about 0.8 requests in flight. Autoscaling still responds correctly, because it acts on sustained concurrency rather than sub-second bursts.

***

## CPU usage and memory

Displays resource utilization across replicas. Metrics are averaged and may not capture short spikes.

### Considerations:

* **High CPU/memory usage**: May degrade performance. Consider upgrading to a larger instance type.
* **Low CPU/memory usage**: Possible overprovisioning. Switch to a smaller instance to reduce costs.

***

## GPU usage and memory

Shows GPU utilization across replicas.

* **GPU usage**: Percentage of time a kernel function occupies the GPU.
* **GPU memory**: Total memory used.

### Considerations:

* **High GPU load**: Can slow inference. Check response time metrics.
* **High memory usage**: May cause out-of-memory failures.
* **Low utilization**: May indicate overprovisioning. Consider a smaller GPU.

***

## vLLM and SGLang metrics

When your deployment serves an LLM with [vLLM](/examples/vllm) or [SGLang](/examples/sglang), Baseten surfaces engine-native metrics in the Metrics tab alongside the standard ones. These graphs report what the inference engine itself measures: metrics like tokens per second, time to first token, KV cache usage, and the number of requests running or queued.

<MiniEngineThroughput />

### How detection works

You don't turn these graphs on manually. Baseten scrapes your container's `/metrics` endpoint and looks for metrics that match the vLLM or SGLang format. When it finds them, the matching graphs appear in the Metrics tab automatically. No configuration or redeploy is required.

If you don't see the graphs, and they don't appear in the **Customize view** panel either, Baseten was most likely unable to read your container's metrics endpoint. Common causes are that the endpoint isn't exposed, it's blocking Baseten's scrape, or the engine isn't emitting metrics yet. Confirm that your engine serves Prometheus metrics on its `/metrics` route. For [custom servers](/development/model/custom-server), routes like `/metrics` pass through to your server unchanged.

<Note>
  Detection runs on a periodic scrape and results are cached, so a deployment that just started exporting metrics may take a few minutes to show its graphs.
</Note>

### Show and hide graphs

Many of these engine graphs are hidden by default. Turn them on with [Customize your view](#customize-your-view).

The exact graphs depend on what your engine version emits. The latency graphs are shown at the p50, p90, p95, and p99 percentiles, and counters are summed over the selected time range.

### Export engine metrics

The Metrics tab shows a curated set of graphs. You can also export the underlying vLLM and SGLang metrics, along with a few that aren't graphed in the dashboard, to your own observability stack through the [metrics export endpoint](/observability/export-metrics/overview). See [vLLM and SGLang metrics](/observability/export-metrics/supported-metrics#vllm-and-sglang-metrics) for the labels Baseten adds.

***

## Async queue metrics

* **Time in Async Queue**: Time spent in the async queue before execution (p50, p90, p95, p99).
* **Async Queue Size**: Number of queued async requests.
* **Webhook requests**: Number of [async webhook](/inference/async) delivery requests sent.
* **Webhook latency**: Latency of async webhook delivery requests (p50, p90, p95, p99).

### Considerations:

* Large queue size indicates requests are queued faster than they are processed.
* To improve async throughput, increase the max replicas or adjust autoscaling concurrency.
* Async Queue Size is a point-in-time gauge, like [concurrent requests](#concurrent-requests). When requests spend little time queued, most samples catch an empty queue and it reads 0 even under steady load.

***

## Use metrics for autoscaling

Use these metrics to diagnose autoscaling behavior and tune your settings.

### Key metrics to watch

| Metric                            | What it tells you                                                                     |
| --------------------------------- | ------------------------------------------------------------------------------------- |
| **Concurrent requests**           | Shows total demand (queued + active). This is the signal driving autoscaling.         |
| **Replicas** (active vs starting) | Shows scaling activity. Large gaps indicate cold start delays.                        |
| **Inference volume**              | Shows traffic patterns. Use to identify if you have noisy, bursty, or steady traffic. |
| **Response time** (p95, p99)      | Shows if scaling is keeping up. Spikes aligned with replica changes indicate thrash.  |
| **Async queue size**              | Shows backpressure. Growing queue means you need more capacity.                       |

### Diagnose autoscaling issues

| You see...                                        | Likely cause                | Fix                                             |
| ------------------------------------------------- | --------------------------- | ----------------------------------------------- |
| Latency spikes aligned with replica count changes | Oscillation (thrash)        | Increase scale-down delay                       |
| Replicas at max, latency still degrading          | Insufficient capacity       | Increase max replicas or concurrency target     |
| Large gap between active and starting replicas    | Cold start delays           | Increase min replicas, check image optimization |
| Traffic high but replicas staying low             | Concurrency target too high | Lower concurrency target or target utilization  |
| Replicas scaling down too quickly                 | Scale-down delay too short  | Increase scale-down delay                       |

For solutions to common autoscaling problems, see [Autoscaling troubleshooting](/troubleshooting/deployments#autoscaling-issues).
