# Migrate from Engine-Builder-LLM
Source: https://docs.baseten.co/engines/bis-llm/migrate-from-v1

Translate a v1 Engine-Builder-LLM configuration to BIS-LLM (v2), including the autoscaling, speculation, and routing changes that aren't just renames

Engine-Builder-LLM is the v1 inference stack. BIS-LLM is the v2 stack. The two share much of the same `trt_llm` schema but differ in what counts as build configuration, what counts as runtime configuration, and how autoscaling, speculation, and routing work. This page covers the field-by-field translation and the semantic changes that aren't just renames.

## The shape change

v2 simplifies the `build:` section to five fields (`checkpoint_repository`, `quantization_type`, `quantization_config`, `num_builder_gpus`, `skip_build_result`) and moves everything else to `runtime:`. The build validator rejects v1-only fields under `build:` with explicit error messages.

**v1 (Engine-Builder-LLM):**

```yaml config.yaml theme={"system"}
trt_llm:
  build:
    base_model: decoder
    checkpoint_repository:
      source: HF
      repo: "Qwen/Qwen3-4B"
    max_seq_len: 32768
    max_batch_size: 256
    max_num_tokens: 8192
    quantization_type: fp8_kv
    tensor_parallel_count: 1
    plugin_configuration:
      paged_kv_cache: true
      use_paged_context_fmha: true
      use_fp8_context_fmha: true
  runtime:
    kv_cache_free_gpu_mem_fraction: 0.9
    enable_chunked_context: true
```

**v2 (BIS-LLM):**

```yaml config.yaml theme={"system"}
trt_llm:
  inference_stack: v2
  build:
    checkpoint_repository:
      source: HF
      repo: "Qwen/Qwen3-4B"
    quantization_type: fp8_kv
  runtime:
    max_seq_len: 32768
    max_batch_size: 256
    max_num_tokens: 8192
    tensor_parallel_size: 1
    enable_chunked_prefill: true
```

## Migration steps

Apply these seven changes to translate the v1 build configuration to v2. The order matters only for step 1 (the inference stack declaration must come first); the rest are independent.

1. Add `inference_stack: v2` at the top of `trt_llm:`.
2. Remove `base_model`. v2 detects the architecture from the checkpoint automatically.
3. Move `max_seq_len`, `max_batch_size`, and `max_num_tokens` from `build:` to `runtime:`.
4. Rename `tensor_parallel_count` to `tensor_parallel_size` and move it to `runtime:`.
5. Remove `plugin_configuration`. v2 handles `paged_kv_cache`, `use_paged_context_fmha`, and `use_fp8_context_fmha` automatically.
6. Remove `speculator`. v1 lookahead decoding is not supported in v2; see [Speculative decoding moves to the Management API](#speculative-decoding-moves-to-the-management-api) below.
7. Replace `enable_chunked_context: true` with `enable_chunked_prefill: true` if it was set.

## Semantic changes (not just renames)

The field translation above keeps your deployment running, but four behaviors change in ways that affect how you should configure and operate the v2 deployment.

### Speculative decoding moves to the Management API

v1 lookahead decoding lives in `config.yaml` under `trt_llm.build.speculator`. v2 doesn't support lookahead. Instead, BIS-LLM offers Eagle, MTP, and N-gram speculative decoding through the Management API `speculative_config` block, not through `config.yaml`. See [Speculative decoding](/engines/bis-llm/advanced-features#speculative-decoding) for the configuration shape. Eagle and MTP require Enterprise; [contact your Baseten representative](mailto:support@baseten.co) to enable.

### Autoscaling switches to token-based

v1 deployments use Baseten's [standard request-concurrency autoscaler](/deployment/autoscaling/overview): replicas scale based on `concurrency_target` and `target_utilization_percentage`. v2 deployments use [token-based autoscaling](/engines/performance-concepts/autoscaling-engines#bis-llm) instead: scale on `target_in_flight_tokens`. The v2 deployment API rejects `concurrency_target` and `target_utilization_percentage`. Convert your v1 concurrency target to a token target using:

```math theme={"system"}
target\_in\_flight\_tokens = concurrency\_target × average\_tokens\_per\_request
```

For a model averaging 4K input and 1K output tokens at v1 `concurrency_target` of 10, the v2 token target is roughly 50,000.

### KV-aware routing becomes available

v1 has no equivalent. Workloads with prefix-overlapping requests (long shared system prompts, multi-turn conversations, agentic loops) can enable [KV-aware routing](/engines/bis-llm/advanced-features#kv-aware-routing) on the v2 deployment to substantially reduce time-to-first-token through cache reuse. KV-aware routing requires Enterprise.

### Disaggregated serving becomes available

v1 has no equivalent. Workloads with high prefill-to-decode imbalance (long-context inference, mixed-length traffic) can use [disaggregated serving](/engines/bis-llm/advanced-features#disaggregated-serving) to split prefill and decode onto independent replica groups. Disaggregated serving requires Enterprise.

## Validation errors you might see

The v2 build validator rejects v1-only fields with explicit errors. The most common during migration:

| Error                                                                                   | Cause                                                                                                                                    | Fix                                                                                |
| --------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `Field trt_llm.build.base_model is not allowed to be set when using v2 inference stack` | `base_model` left in `build:`                                                                                                            | Remove. v2 auto-detects from the checkpoint.                                       |
| `Field trt_llm.build.<field> is not allowed to be set when using v2 inference stack`    | v1 runtime fields (`max_seq_len`, `max_batch_size`, `max_num_tokens`, `tensor_parallel_count`, `plugin_configuration`) still in `build:` | Move them to `runtime:`. Rename `tensor_parallel_count` to `tensor_parallel_size`. |
| `Field trt_llm.build.speculator is not allowed to be set when using v2 inference stack` | `speculator` block kept from v1                                                                                                          | Remove. Use the Management API `speculative_config` block instead.                 |

## After migrating

Watch these metrics during and after the cutover:

* `tps_per_request` and `concurrent_requests` should stay similar or improve.
* `autoscaler_in_flight_tokens` is the new load signal. Tune `target_in_flight_tokens` based on observed values; aim for the [50,000-150,000 starting range](/engines/performance-concepts/autoscaling-engines#set-target-in-flight-tokens).
* `speculation_rate` is available once Eagle or MTP is configured through the Management API.

See [BIS-LLM observability](/engines/bis-llm/overview#observability) for the full metric set across the three monitoring domains.

## Related

* [BIS-LLM overview](/engines/bis-llm/overview): Main engine documentation.
* [BIS-LLM configuration](/engines/bis-llm/bis-llm-config): Complete v2 YAML reference.
* [Engine-Builder-LLM configuration](/engines/engine-builder-llm/engine-builder-config): v1 reference for comparison.
* [Token-based autoscaling](/engines/performance-concepts/autoscaling-engines#bis-llm): v2 autoscaling configuration.
* [Speculative decoding](/engines/bis-llm/advanced-features#speculative-decoding): v2 speculative decoding (Eagle, MTP, N-gram).
