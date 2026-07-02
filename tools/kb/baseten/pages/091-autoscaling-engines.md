# Autoscaling engines
Source: https://docs.baseten.co/engines/performance-concepts/autoscaling-engines

Engine-specific autoscaling settings for BEI, Engine-Builder-LLM, and BIS-LLM

BEI, Engine-Builder-LLM, and BIS-LLM batch requests for throughput, so they need different autoscaling settings than standard models. BEI and Engine-Builder-LLM scale on **request concurrency** with engine-tuned targets. BIS-LLM scales on **target in-flight tokens** to account for the wide variance in LLM request size.

## Quick reference

| Setting                    | BEI                                             | Engine-Builder-LLM            |
| -------------------------- | ----------------------------------------------- | ----------------------------- |
| **Target utilization**     | 25%                                             | 40-50%                        |
| **Concurrency target**     | 96+ (min >= 8)                                  | 32-256                        |
| **Special considerations** | Use Performance client for multi-payload routes | Never exceed max\_batch\_size |

BIS-LLM uses a token-aware metric instead of request concurrency. See the [BIS-LLM](#bis-llm) section.

For general autoscaling concepts, see [Autoscaling](/deployment/autoscaling/overview).

***

## BEI

BEI provides millisecond-range inference times and scales differently than other models. With too few replicas, backpressure can build up quickly.

### Recommendations

| Setting            | Value              | Why                                             |
| ------------------ | ------------------ | ----------------------------------------------- |
| Target utilization | **25%**            | Low target provides headroom for traffic spikes |
| Concurrency target | **96+** (min >= 8) | High concurrency allows maximum throughput      |
| Autoscaling        | **Enabled**        | Required for variable traffic                   |

### Multi-payload routes

The `/rerank` and `/v1/embeddings` routes can send multiple items per request, which challenges request-based autoscaling. Each API call counts as one request regardless of how many items it contains.

Use the [Performance client](/inference/performance-client) for optimal scaling with multi-payload routes.

***

## Engine-Builder-LLM

Engine-Builder-LLM uses dynamic batching similar to BEI but doesn't face the multi-payload challenge.

### Recommendations

| Setting            | Value      | Why                                    |
| ------------------ | ---------- | -------------------------------------- |
| Target utilization | **40-50%** | Accommodates dynamic batching behavior |
| Concurrency target | **32-256** | Match or stay below max\_batch\_size   |
| Min concurrency    | **>= 8**   | Optimal performance floor              |

### Concurrency target vs `max_batch_size`

`concurrency_target` tells the autoscaler how many concurrent requests each replica should handle. `max_batch_size` tells the engine how many sequences to batch in a single forward pass. They measure different things: concurrency is a scaling signal, batch size is an engine limit.

Setting `concurrency_target` higher than `max_batch_size` causes on-replica queueing. The autoscaler sends more requests than the engine can batch, and excess requests wait instead of scaling to a new replica. Always keep `concurrency_target` at or below `max_batch_size`.

### Lookahead decoding

If using lookahead decoding, set concurrency target to the same or slightly below `max_batch_size`. This allows lookahead to perform optimizations. This guidance applies to all Engine-Builder-LLM deployments, not just those using lookahead.

***

## BIS-LLM

BIS-LLM autoscales differently from Baseten's other engines. The [standard Baseten autoscaler](/deployment/autoscaling/overview) divides **in-flight requests** by a per-replica concurrency target to decide how many replicas to run. That works when requests cost about the same to serve, but LLM requests don't. One prompt might decode 50 tokens; the next might decode 10,000. Counting them as equal load over-provisions on short prompts and under-provisions on long ones.

The BIS-LLM engine scales on **target in-flight tokens** instead. An in-flight token is any token a replica is currently working on. The deployment API rejects `concurrency_target` and `target_utilization_percentage`. Configure scaling with `target_in_flight_tokens` only (replica bounds in the table below).

<MiniTokenScaling />

### How in-flight tokens are counted

The Planner's load measure is the sum of two per-worker counts:

* **Prefill tokens:** the uncached input tokens currently being processed across active requests. Tokens served from KV cache reuse do not count.
* **Decode tokens:** the full sequence length (input plus tokens generated so far) for every request currently decoding.

This is why request count alone misses the real load: a long-context decode with a 100K-token KV cache contributes 100K to the load measure even though it is "just one request."

The total across the deployment roughly equals `active_requests × average_tokens_per_request`, which makes targets easy to derive from request-based intuition.

### What you configure

You configure four standard fields plus a token target. All five are editable from the deployment's autoscaling settings in the Baseten UI.

```yaml config.yaml theme={"system"}
autoscaling_settings:
  min_replica: 1
  max_replica: 4
  autoscaling_window: 300   # seconds; recommended 300 (5 minutes)
  scale_down_delay: 300     # seconds; recommended 300 (5 minutes)

additional_autoscaling_config:
  metrics:
    - name: in_flight_tokens
      target: 40000
```

| Setting                       | What it controls                                                                                                                                                                                                       |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `min_replica` / `max_replica` | Replica bounds. Scale-to-zero is not supported. `min_replica` defaults to `1` when omitted. Set `max_replica` to cap scale-up during cold starts.                                                                      |
| `autoscaling_window`          | Sliding window (in seconds) used to average in-flight tokens before making a scaling decision. Longer windows smooth out short spikes; shorter windows react faster. A 5-minute (300s) window is a reasonable default. |
| `scale_down_delay`            | Waiting period (in seconds) before removing replicas after load drops.                                                                                                                                                 |
| `metrics.target`              | Target in-flight tokens per replica. This is the primary knob to tune.                                                                                                                                                 |

### Set target in-flight tokens

For most LLMs, a target in the **50,000 to 150,000** range is a sensible starting point. From there:

* **Lower target:** more replicas at a given load. More headroom, higher cost.
* **Higher target:** fewer replicas at a given load. Less headroom, lower cost.

If you're coming from another engine and already have a request concurrency target in mind, convert it directly. In-flight tokens roughly equals `active_requests × average_tokens_per_request`, so:

```math theme={"system"}
target = concurrency\_target × average\_tokens\_per\_request
```

`average_tokens_per_request` is approximately `average_input_tokens + average_output_tokens`. For a model averaging 4K input and 1K output tokens at a concurrency of 10:

```math theme={"system"}
target = 5{,}000 × 10 = 50{,}000
```

Once a target is set, the autoscaler computes desired replicas as:

```math theme={"system"}
desired\_replicas = avg\_in\_flight\_tokens / target\_in\_flight\_tokens
```

Start conservatively and adjust based on observed latency.

### Graceful scale-down with `scale_down_half_life_seconds`

Kubernetes (through Knative) allows scale-down of up to **50% of replicas per step**. For most services this is fine, but BIS-LLM deployments hold KV cache state on each worker. A sudden 50% drop in replica count means a 50% loss of KV cache space, which causes a wave of cache misses and TTFT spikes for cache-sensitive workloads (long shared system prompts, multi-turn conversations).

`scale_down_half_life_seconds` applies **exponential decay** to the current replica count, lowering it gradually over the configured half-life rather than allowing a single large drop. The default is **900 seconds (15 minutes)**, which keeps KV cache erosion gradual. Set it shorter to release capacity faster and shed KV cache state more abruptly; set it longer to keep replicas (and their cache) around for more reuse.

This setting lives in `b10_autoscaling_config` in the `llm_config` block of the Management API (`POST /v1/llm_models`), not in Truss `config.yaml`. It is not configurable from the UI.

```json theme={"system"}
{
  "b10_autoscaling_config": {
    "scale_down_half_life_seconds": 900
  }
}
```

Recommended range: 600-1800 seconds. Setting it shorter risks the same abrupt KV cache loss the setting exists to prevent. Setting it longer wastes GPU cost.

### Known issues

Two failure modes are structural to the autoscaling loop, not configuration mistakes.

**Scale-up overshoot during rapid load increase.** Workers take time to start (model loading and warmup). Until they are healthy, they are not counted in the autoscaler's worker pool, so the Planner continues to see high per-worker load and keeps requesting more replicas. By the time all the new workers are healthy, the deployment may be over-provisioned.

Mitigation: set `max_replica` to cap the overshoot. Cold start time is the underlying constraint; there is no way to fully prevent this without reducing it.

**Scale-down thrashing and KV cache loss.** When workers scale down, their KV cache disappears with them. Aggressive or frequent scale-down forces full prefill on requests that would otherwise have hit cache (higher TTFT), and if many replicas drop at once a large fraction of total KV cache space vanishes simultaneously.

Mitigation: set `scale_down_half_life_seconds` to 600-1800 seconds and keep `scale_down_delay` modest. The half-life exists specifically to prevent abrupt large-scale downscales.

### Monitoring

The Planner emits autoscaler metrics directly. Start with `autoscaler_in_flight_tokens` to see what the autoscaler is currently observing, then reach for the averaged and policy-applied metrics when tuning.

| Metric                             | Type  | What it measures                                                                                                                                 |
| ---------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `autoscaler_in_flight_tokens`      | Gauge | Instantaneous in-flight tokens across all workers. The primary product-visible metric, labeled with `exported_namespace` and `model_version_id`. |
| `autoscaler_avg_in_flight_tokens`  | Gauge | Sliding-window average used for scaling decisions.                                                                                               |
| `autoscaler_avg_num_requests`      | Gauge | Sliding-window average request count across all workers.                                                                                         |
| `autoscaler_avg_num_workers`       | Gauge | Sliding-window average healthy worker count. The denominator for per-worker load.                                                                |
| `autoscaler_desired_scale`         | Gauge | Raw desired scale from the token-based autoscaler, before policy.                                                                                |
| `autoscaler_policy_desired_scale`  | Gauge | Desired scale after policy is applied.                                                                                                           |
| `autoscaler_rounded_desired_scale` | Gauge | Final integer scale sent to Kubernetes.                                                                                                          |

What to watch:

* `autoscaler_rounded_desired_scale` pinned at `max_replica` for extended periods means the deployment is capacity-constrained. Raise the cap or the target.
* A large persistent gap between `autoscaler_desired_scale` and the actual replica count means scaling is too slow in one direction. Tune `autoscaling_window` for scale-up or `scale_down_half_life_seconds` for scale-down.

***

## Related

* [Configure autoscaling parameters](/deployment/autoscaling/overview): Full parameter reference.
* [Match autoscaling to your traffic pattern](/deployment/autoscaling/traffic-patterns): Pattern-specific settings.
* [Deploy BEI embedding models](/engines/bei/overview): General BEI documentation.
* [Deploy Engine-Builder-LLM models](/engines/engine-builder-llm/overview): Generation model details.
* [Deploy BIS-LLM models](/engines/bis-llm/overview): MoE and advanced LLM engine details.
* [Maximize throughput with the Performance Client](/inference/performance-client): Client usage for batch processing.
