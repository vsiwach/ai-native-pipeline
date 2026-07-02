# DEBUG.md — Why three dedicated Qwen3-8B deployments failed (docs-grounded)

Prepared 2026-07-02 by the `baseten-docs` agent from the docs.baseten.co snapshot at
`tools/kb/baseten/` (394 pages). Every claim below quotes the doc page and cites its
`Source:` URL. Failure narrative from `docs/FRICTION_LOG.md` #1–2, #6–7, #12.

---

## Failure 3 (most recent): `qz47j5o` — Engine-Builder-LLM, H100, `BUILD_FAILED`

Config at time of failure: `deploy/baseten/config.yaml` (py313, H100, cpu '1',
memory 10Gi, `trt_llm.build` with `base_model: decoder`, `Qwen/Qwen3-8B`,
`max_seq_len 8192`, `quantization_type: fp8_kv`, `tensor_parallel_count 1`).

What `BUILD_FAILED` means, per docs:

> "**Build failed**: The deployment is not active due to a Docker build failure."
> — Source: https://docs.baseten.co/observability/health

The build step for Engine-Builder is where weights are downloaded and quantized:

> "For Engine-Builder-LLM, Baseten downloads model weights from the source repository
> (Hugging Face, S3, or GCS) and compiles them with TensorRT-LLM. Compilation builds
> optimized CUDA kernels for the target GPU architecture, applies quantization if
> configured…"
> — Source: https://docs.baseten.co/concepts/howbasetenworks

### Line-by-line audit of the failed config against the docs

| Config line | Verdict | Doc evidence |
|---|---|---|
| `resources.cpu: '1'` / `memory: 10Gi` | **Contradicts every documented ≥8B example; #1 suspect** | The docs' own Engine-Builder sizing scales host resources with model size: 3B example → `cpu: '1' / memory: 10Gi`; 32B → `cpu: '2' / memory: 20Gi`; 70B → `cpu: '4' / memory: 40Gi` ("Configuration examples", https://docs.baseten.co/engines/engine-builder-llm/engine-builder-config). We gave an 8B fp8_kv build the 3B footprint. Critically, the docs name CPU-memory exhaustion as a known **build-job** failure mode and its fix: "If you run out of CPU memory, add more memory in the `resources` section instead." (`num_builder_gpus` field, https://docs.baseten.co/reference/truss-configuration). An fp8_kv build must pull and materialize the ~16 GB BF16 checkpoint plus run calibration; 10 Gi host RAM is below the weights themselves. This is also exactly the failure shape we already proved on the T4 (friction #7: host-RAM OOM loading 8B weights on a 16 GiB box). |
| `quantization_type: fp8_kv` | **Valid** — not the cause | Enum: "`quantization_type: no_quant \| fp8 \| fp8_kv \| fp4 \| fp4_kv \| fp4_mlp_only`" and H100 supports it: GPU support table shows **H100: FP8 ✅ FP8_KV ✅** (https://docs.baseten.co/engines/performance-concepts/quantization-guide). The bias caveat is Qwen2-only: "Qwen2 retains QKV projection bias… so `FP8_KV` causes quality degradation. Use regular `FP8` instead" — "Qwen3, Llama3… remove it" (same page). Truss ref concurs: "fp8_kv… Not compatible with models that use `bias=True` (for example, Qwen 2.5)." (https://docs.baseten.co/reference/truss-configuration). Docs even recommend it: "Use `quantization_type: fp8_kv` for best performance/accuracy balance." (https://docs.baseten.co/engines/engine-builder-llm/engine-builder-config) |
| `base_model: decoder` + `Qwen/Qwen3-8B` | **Valid** — supported family | Architecture table: "**Qwen** \| `Qwen2ForCausalLM`, `Qwen3ForCausalLM` \| Including Qwen 2.5 and Qwen 3 series." (https://docs.baseten.co/engines/engine-builder-llm/engine-builder-config). Overview maps "`Qwen3ForCausalLM` → Qwen3 backend" and cites "4000 tokens/s per request on Qwen-3-8B with a single H100" (https://docs.baseten.co/engines/engine-builder-llm/overview). Checkpoint rules satisfied: BF16, safetensors, not pre-quantized ("Cannot be a pre-quantized model. Model must be an `fp16`, `bf16`, or `fp32` checkpoint.", engine-builder-config). |
| `python_version: py313` | **Not documented as invalid, but off the documented path — #2 suspect** | The Truss reference lists `py313` as supported (https://docs.baseten.co/reference/truss-configuration), and one official `trt_llm` example uses it — but on the **v2/BIS** stack (https://docs.baseten.co/examples/models/llm/llama-3.3). The customize-a-model page lists only "`py39`, `py310`, `py311`, `py312`" (https://docs.baseten.co/examples/models/deepseek/deepseek-v3 sibling page, https://docs.baseten.co/development/model/customize-a-model), and **none of the Engine-Builder-LLM (v1) example configs set `python_version` at all** (all three examples in https://docs.baseten.co/engines/engine-builder-llm/engine-builder-config omit it). The engine build supplies its own image; the field is at best noise, at worst an untested combination. Removed. |
| `max_seq_len: 8192` | Valid | "**Optional.** Maximum sequence length… Range: 1 to 1048576." (engine-builder-config) |
| `tensor_parallel_count: 1` on `accelerator: H100` | Valid | "Must equal the number of GPUs in your `accelerator` resource setting." (engine-builder-config) — 1 GPU, TP1 ✓ |
| Missing `runtime.total_token_limit`, `build.max_batch_size`, `max_num_tokens`, `plugin_configuration`, `quantization_config` | **Not errors** — all Optional | Only two build fields are marked **Required**: `base_model` and `checkpoint_repository` ("Fields are tagged Required, Optional, or Computed", engine-builder-config). But every documented fp8_kv example ships `plugin_configuration` (paged_kv_cache / use_paged_context_fmha / use_fp8_context_fmha) and a `quantization_config` calibration block; added to match the documented shape. |
| Missing `inference_stack: v1` | Not an error | The reference schema shows "`inference_stack: v1  # Always v1 for Engine-Builder-LLM`" but all three official examples omit it (engine-builder-config); v1 is the default. |
| `accelerator: H100` | **Correct per docs** | Model size support: "8B-30B \| H100, B200 \| TP1 \| **H100**" (https://docs.baseten.co/engines/engine-builder-llm/overview); best-practices table repeats "8B-30B → H100, FP8/FP8_KV, TP 1" (engine-builder-config). |

**Ranked root-cause verdict:** (1) build-job host-memory starvation from
`cpu: '1' / memory: 10Gi` — the only config line that contradicts the documented
examples for this model class, with a documented failure mode and fix; (2) `py313`
on the v1 engine path — legal per the reference enum but absent from every v1
example; (3) missing calibration/plugin blocks — optional, but the failed config is
the only fp8_kv shape not shown in the docs. Build logs are console-only (friction
#12), so this ranking is the best the docs corpus supports.

---

## Failure 1: `wno2dv0` — L4, never scheduled in 30+ min → INACTIVE

* **The L4 SKU we hit is documented as a 2-GPU node.** Instance type reference:
  "`L4:2x24x96` \| \$0.04002 \| 24 vCPU \| 96 GiB \| **2 NVIDIA L4s** \| 48 GiB"
  — Source: https://docs.baseten.co/deployment/resources
  A single-L4 SKU **does** exist per the same table — "`L4:4x16` \| \$0.01414 \| 4 \|
  16 GiB \| 1 NVIDIA L4 \| 24 GiB" — but note its host RAM is 16 GiB, the same trap
  that killed failure 2. Selection rule: "Baseten provisions the **smallest instance
  that meets the specified constraints**" — asking for >16 Gi memory or >4 CPUs with
  `accelerator: L4` lands you on the 2×L4 node.
* **L4 for LLM serving is a documented anti-pattern regardless of scheduling.** GPU
  details: "**L4** … 24 GiB VRAM, 300 GiB/s … **Limit: Not suitable for LLMs due to
  bandwidth**" — Source: https://docs.baseten.co/deployment/resources. The
  Engine-Builder model-size table never lists L4 for any generative size class
  (smallest row is "`<8B` → H100_40GB, H100, B200",
  https://docs.baseten.co/engines/engine-builder-llm/overview).
* **Capacity/scheduling expectations:** the docs make availability claims at the
  control-plane level — "if a region or provider faces a capacity crunch or outage,
  MCM re-routes and re-provisions workloads to maintain service continuity"
  (https://docs.baseten.co/concepts/howbasetenworks) — but document **no** queue
  position, ETA, or per-SKU stock signal for deploy-time scheduling. The only
  documented capacity constraint is "H200 and B200 instances are available on
  request" (https://docs.baseten.co/deployment/resources). The 30-minute silent
  `DEPLOYING → INACTIVE` has no documented semantics; the health page defines
  Inactive only as "unavailable and not consuming resources… may be manually
  reactivated" (https://docs.baseten.co/observability/health). Friction #6's product
  gap stands.

## Failure 2: `w52ym5j` — T4x4x16, host-RAM OOM crash-loop loading int4-AWQ 8B

* **The SKU's 16 GiB host RAM is documented:** "`T4x4x16` \| \$0.01052 \| 4 vCPU \|
  **16 GiB RAM** \| 1 NVIDIA T4 \| 16 GiB VRAM" — Source:
  https://docs.baseten.co/deployment/resources
* **The docs' T4 guidance tops out well below 8B:** "**T4** … **Best for:** Whisper,
  small LLMs like **StableLM 3B**" (same page). An 8B — even int4-quantized to ~6 GB
  of weights — is outside the documented T4 workload envelope.
* **No page states a minimum host-RAM-to-weights ratio.** The closest the docs come
  is the generic warning "**Insufficient resources**: Slow inference or failures."
  (https://docs.baseten.co/deployment/resources) and, for build jobs, "If you run out
  of CPU memory, add more memory in the `resources` section instead."
  (https://docs.baseten.co/reference/truss-configuration). There is no documented
  pre-flight of model footprint vs. instance RAM — friction #7's ask is real.
* **Side note for any future engine-builder attempt:** the AWQ checkpoint itself is a
  dead end on the engine path — "Non-ModelOpt pre-quantized checkpoints (for example,
  GPTQ or **AWQ** safetensors) **are not supported**. The build rejects them with an
  error." — Source: https://docs.baseten.co/engines/performance-concepts/quantization-guide

---

## The documented recommended path for Qwen3-8B-class dedicated serving

* **Engine choice — Engine-Builder-LLM, explicitly:** "**Dense text-generation LLMs**
  (`Llama 3` or `4`, **`Qwen 3` or `3.5`**, `Mistral`, `Gemma`, `Phi`, `GPT-OSS-20B`):
  use **Engine-Builder-LLM**" — Source: https://docs.baseten.co/engines/index.
  BIS-LLM is not self-serve ("**Self-serviceable** \| 🔒 \| ✅ … BIS-LLM requires
  Enterprise", same page; "Currently a co-engineering pilot"). Custom Truss is the
  documented fallback only for "Speech, image, video, or custom Python models".
* **GPU choice — single H100, TP1, fp8_kv:** "8B-30B \| H100, B200 \| TP1 \|
  **H100**" (https://docs.baseten.co/engines/engine-builder-llm/overview); best
  practices: "8B-30B \| H100 / B200 \| FP8 / FP8_KV \| 1"
  (https://docs.baseten.co/engines/engine-builder-llm/engine-builder-config). The
  overview's own performance claim for this exact model is "4000 tokens/s per request
  on **Qwen-3-8B with a single H100**". Instance: `H100` = \$0.10833/min, 16 vCPU,
  118 GiB RAM, 80 GiB VRAM (https://docs.baseten.co/deployment/resources). The
  fractional `H100MIG` (\$0.06250/min, 40 GiB VRAM) is documented only for the
  `<8B` row ("H100_40GB (cost-effective)"), and Qwen3-8B sits in the 8B-30B row, so
  H100 is the cheapest GPU the docs list as compatible for this model.

## What to change (applied in `deploy/baseten/config.yaml`)

| Line | Was | Now | Why (doc) |
|---|---|---|---|
| `resources.cpu` / `memory` | `'1'` / `10Gi` | `'2'` / `20Gi` | Match the documented H100 fp8_kv example scale (32B uses 2/20Gi; 3B uses 1/10Gi); documented fix for build CPU-memory OOM is raising `resources.memory` (engine-builder-config; truss-configuration) |
| `python_version` | `py313` | *(removed)* | No Engine-Builder-LLM (v1) example sets it; eliminates the one unvalidated field (engine-builder-config examples) |
| `build.max_batch_size` | *(absent)* | `256` | "Keep this at 256." (engine-builder-config) |
| `build.max_num_tokens` | *(absent)* | `8192` | "Recommended: `8192` or `16384`." (engine-builder-config) |
| `build.plugin_configuration` | *(absent)* | paged_kv_cache / use_paged_context_fmha / use_fp8_context_fmha: true | "Enable `paged_kv_cache` and `use_paged_context_fmha` for optimal performance"; `use_fp8_context_fmha` "requires `fp8_kv`" — we have it (engine-builder-config) |
| `build.quantization_config` | *(absent)* | calib_size 1024, cnn_dailymail, max_seq 2048 | Every documented fp8_kv example ships a calibration block (engine-builder-config) |
| `build.checkpoint_repository.revision` | *(absent)* | `main` | Matches documented example shape (engine-builder-config) |
| `runtime.*` (kv fraction 0.9, served_model_name) | kept | + `enable_chunked_context: true`, `batch_scheduler_policy: guaranteed_no_evict` | Documented production defaults (engine-builder-config) |
| `accelerator` | `H100` | `H100` (unchanged) | "8B-30B → H100, TP1" (engine-builder-llm/overview) |
