# Advanced features for BIS-LLM
Source: https://docs.baseten.co/engines/bis-llm/advanced-features

KV-aware routing, disaggregated serving, and speculative decoding

BIS-LLM ships three Enterprise-gated production features that target distinct bottlenecks in large-scale LLM serving: KV-aware routing reduces time-to-first-token on repeated prefixes, disaggregated serving prevents long prefills from blocking decode latency, and speculative decoding raises throughput on a single replica. Each section uses the same shape: how it works, configuration, when to use it, and the metric to watch.

All three are configured through the BIS-LLM Management API (`POST /v1/llm_models`) under the `llm_config` block, not through Truss `config.yaml`. To enable any of them on your deployment, [contact your Baseten representative](mailto:support@baseten.co).

## KV-aware routing

Long prompts repeat context across requests. Without cache-aware routing, each worker rebuilds KV state from scratch on every request, even when another worker in the deployment already has the prefix cached. The KV-aware router maintains a real-time index of every worker's KV cache contents and picks the worker most likely to serve a request from cache.

### How it works

The router runs as a stateful service in front of the BIS-LLM worker pool. For each incoming request:

1. The frontend tokenizes the prompt and calls the router for a worker assignment.
2. The router scores each worker against the prompt's tokens using a radix tree that indexes every worker's KV cache.
3. The router returns the worker most likely to serve the request from cache, balanced against current worker load.
4. The frontend sends the request directly to that worker.

Workers publish KV cache block events as blocks are added or evicted; the router consumes those events to keep its index in sync. The router periodically writes index snapshots to persistent storage so it can recover state on restart without replaying every event.

### Configuration

Settings live under `b10_routing_config`. Defaults match production Model APIs and rarely need to change.

```json theme={"system"}
{
  "b10_routing_config": {
    "router_queue_policy": "fcfs",
    "router_overlap_score_weight": 3.5,
    "router_temperature": 0.05
  }
}
```

<ParamField type="string">
  How queued requests are ordered when all workers are saturated. Queueing rarely triggers under normal load.

  * `fcfs`: First-come, first-served with priority bumps. Optimizes tail TTFT and provides fairness.
  * `wspt`: Weighted shortest processing time. Prioritizes cheaper requests (high cache hit, short prompts). Risks starving costly requests; use when average TTFT matters more than tail TTFT.
</ParamField>

<ParamField type="number">
  Bias toward cache hits versus load balance. Higher values bias toward cache hits at the cost of balance; lower values bias toward balance at the cost of hits. [Contact us](mailto:support@baseten.co) before changing in production.
</ParamField>

<ParamField type="number">
  Randomness in worker selection. Higher values spread load across more workers; lower values concentrate hits on fewer workers. [Contact us](mailto:support@baseten.co) before changing in production.
</ParamField>

A single active router becomes a bottleneck above roughly 50 workers. For larger deployments, the router can run as multiple active replicas that share in-flight request state. [Contact us](mailto:support@baseten.co) to add router replicas.

### When to use

KV-aware routing is on by default for BIS-LLM deployments and pays off whenever prompts share prefixes: agent loops, chat with long system messages, RAG pipelines reusing retrieved context, and code completion. Workloads with no prefix overlap (unique single-turn prompts) see only the load-balancing benefit.

### Monitoring

| Metric                          | What it measures                                              | What to look for                                                                                             |
| ------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `kv_cache_hit_rate`             | Actual KV cache hit rate observed by workers.                 | Baseline varies by model and traffic. Track changes over time, not absolute values.                          |
| `kv_cache_hit_rate_skew`        | Router's estimated hit rate minus actual hit rate.            | Typically slightly positive (\~+10%). Large positive: high cache churn. Large negative: missed event stream. |
| `kv_cache_best_prefix_hit_rate` | Best hit rate the router could have selected given its index. | Upper bound of routing quality for the current index.                                                        |
| `kv_cache_hit_rate_efficiency`  | Ratio of actual hit rate to best possible.                    | Typically 90-100%. Lower values mean the router is trading hits for balance.                                 |

## Disaggregated serving

In a standard deployment, each replica handles both prefill (prompt processing) and decode (token generation). When a long prompt arrives, the replica must finish prefill before it can decode any tokens, blocking shorter requests queued behind it.

### How it works

Disaggregated serving splits prefill and decode into separate replica groups:

* **Prefill replicas** process input prompts and transfer the resulting KV cache to decode replicas.
* **Decode replicas** receive KV cache from prefill replicas and generate output tokens.

Each phase scales independently based on its own load. A long prefill never blocks decode latency on other replicas.

### Configuration

Set `is_disaggregated` and `b10_disagg_config` in the `llm_config` block:

```json theme={"system"}
{
  "is_disaggregated": true,
  "b10_disagg_config": {
    "prefill_workers_per_replica": 1,
    "decode_workers_per_replica": 2
  }
}
```

<ParamField type="boolean">
  Enables disaggregated serving. Must be `true` for `b10_disagg_config` to take effect. Setting `b10_disagg_config` without `is_disaggregated: true` fails validation.
</ParamField>

<ParamField type="integer">
  Prefill worker pods per replication unit. Must be an integer >= 1.
</ParamField>

<ParamField type="integer">
  Decode worker pods per replication unit. Must be an integer >= 1.
</ParamField>

The two worker counts define a **replication unit**: the smallest independently scalable group. A `prefill: 1, decode: 2` configuration means each unit has one prefill pod and two decode pods. The autoscaler scales the number of units, not individual pods.

The backend rejects deployments where `is_disaggregated` is `false` or absent but `b10_disagg_config` is set, and rejects deployments where `is_disaggregated` is `true` but either worker count is missing or less than one.

### When to use

Disaggregated serving fits deployments with at least one of these traits:

* **Mismatched prefill and decode resource profiles.** Long-context models (128K+ tokens) have compute-heavy prefills and memory-bound decodes. Separate scaling right-sizes each phase.
* **Strict TTFT targets.** Isolating prefill on dedicated replicas prevents decode requests from queuing behind long prompts.
* **Variable prompt lengths.** Mixed short/long workloads benefit more than uniform traffic.

For consistent prompt lengths or workloads where TTFT is not a bottleneck, aggregated serving is simpler and sufficient.

### Monitoring

Watch [BIS-LLM autoscaling metrics](/engines/performance-concepts/autoscaling-engines#bis-llm) on each replica group. Token-based autoscaling sizes prefill and decode independently using their own in-flight token counts.

## Speculative decoding

Speculative decoding accelerates inference by drafting several future tokens cheaply, then verifying them against the main model in a single forward pass. Accepted tokens advance the output; rejected tokens are discarded and the model resumes autoregressive decoding from the last accepted token.

### How it works

BIS-LLM speculative decoding uses a fast draft mechanism (a lightweight Eagle head, the model's own MTP layers, or n-gram automata) to generate candidate tokens. The main model then verifies these candidates in a single batched forward pass. Higher acceptance rates yield more tokens per forward pass and lower latency.

This is a different system from v1 [lookahead decoding](/engines/engine-builder-llm/lookahead-decoding), which uses n-gram patterns within a single model and is configured with `trt_llm.build.speculator`. The v2 stack rejects `trt_llm.build.speculator`; use `speculative_config` instead.

| Decoding type | How it works                                                                    | Best for                                                                   |
| ------------- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `Eagle`       | Separate Eagle head drafts tokens from a hidden-state representation.           | Models with trained Eagle checkpoints.                                     |
| `MTP`         | The model's own multi-token-prediction layers draft multiple tokens per step.   | Models with MTP heads built in (DeepSeek-V3).                              |
| `NGram`       | N-gram automata predict tokens from pattern matching without model computation. | High-throughput workloads where latency matters more than acceptance rate. |

All three share the same loop: the draft mechanism proposes a run of tokens, the model verifies the whole run in one forward pass, and the matching tokens are accepted together. Only the draft source changes. Switch it to compare:

<SpeculativeDecoding />

### Configuration

Set `speculative_config` in the `llm_config` block. The required fields depend on `decoding_type`.

<ParamField type="string">
  Speculative strategy. One of `Eagle`, `MTP`, or `NGram` (case-insensitive).
</ParamField>

<ParamField type="string">
  Required when `decoding_type` is `Eagle`. Path to the Eagle head weights directory. BDN mirrors this as a standalone weight volume, separate from the main model weights.
</ParamField>

<ParamField type="integer">
  Required when `decoding_type` is `MTP`. Number of next-token prediction layers in the model architecture.
</ParamField>

<ParamField type="integer">
  Optional. Maximum number of tokens the draft proposes per step. Raise it for more aggressive speculation, lower it if acceptance is poor.
</ParamField>

<ParamField type="boolean">
  Optional, `Eagle` only. Run the Eagle3 draft head and the target model as a single fused model. Set to `true` for Eagle3 checkpoints that support it.
</ParamField>

Eagle example:

```json theme={"system"}
{
  "speculative_config": {
    "decoding_type": "Eagle",
    "speculative_model_dir": "/models/eagle",
    "max_draft_len": 3,
    "eagle3_one_model": true
  }
}
```

MTP example:

```json theme={"system"}
{
  "speculative_config": {
    "decoding_type": "MTP",
    "num_nextn_predict_layers": 1
  }
}
```

NGram example:

```json theme={"system"}
{
  "speculative_config": {
    "decoding_type": "NGram"
  }
}
```

### When to use

Pick by model architecture, not preference. Use `MTP` for DeepSeek-V3 and other models that ship MTP heads. Use `Eagle` when you have a trained Eagle head for the target model. Use `NGram` for high-throughput workloads where any acceleration helps and no draft model is available.

### Monitoring

The BIS-LLM dashboard exposes `speculation_rate` when speculative decoding is active: the percentage of draft tokens accepted by the main model.

* **Above 80%**: Draft is well-aligned with the main model. Speculation is effective.
* **40-80%**: Some rejections. Consider tuning the draft model or switching decoding types.
* **Below 40%**: Speculation likely costs more than it saves. Disable it or reduce draft length.

## Related

* [BIS-LLM overview](/engines/bis-llm/overview): Engine fundamentals and supported model families.
* [BIS-LLM configuration](/engines/bis-llm/bis-llm-config): Truss `config.yaml` reference for the build step.
* [Autoscaling BIS-LLM](/engines/performance-concepts/autoscaling-engines#bis-llm): Token-based autoscaling for prefill, decode, and aggregated replicas.
* [Lookahead decoding (v1)](/engines/engine-builder-llm/lookahead-decoding): N-gram speculation for Engine-Builder-LLM, when you need the v1 path.
