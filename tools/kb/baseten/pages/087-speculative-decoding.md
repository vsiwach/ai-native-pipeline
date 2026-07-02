# Speculative decoding
Source: https://docs.baseten.co/engines/engine-builder-llm/lookahead-decoding

Lookahead decoding on Engine-Builder-LLM (v1) for code generation and predictable content

Lookahead decoding is a speculative decoding technique that provides 2x-4x faster inference for suitable workloads by predicting future tokens using n-gram patterns. It's particularly effective for coding agents and content with predictable patterns.

## Overview

Lookahead decoding identifies n-gram patterns in the input context and past tokens, speculates on future tokens by generating candidate sequences, verifies those predictions against the model's actual output, and accepts the verified tokens in a single step. The model still produces every token: it accepts the longest run of guessed tokens that matches its own output, and at the first mismatch it keeps that prefix and falls back to its own next token.

The output is identical to decoding token by token: the accepted tokens are exactly what the big model would have produced on its own, so speculative decoding changes only how many tokens clear per pass, not the result. The drafted run length depends on `lookahead_ngram_size`, `lookahead_windows_size`, and `lookahead_verification_set_size`, documented under [Configuration parameters](#configuration-parameters).

The technique works with any model compatible with Engine-Builder-LLM. Baseten's B10 Lookahead implementation searches up to 10M past tokens for n-gram matches across language patterns.

## When to use lookahead decoding

Lookahead decoding excels at code generation where programming language syntax creates predictable patterns, and function signatures, variable names, and common idioms all benefit. It also accelerates prompt lookup scenarios where you provide example completions in the prompt, and general low-latency use cases where you can trade slightly decreased throughput for faster individual responses.

### Limitations

* Lookahead is supported on A10G, L4, A100, H100\_40GB, H200, and H100.
* During speculative decoding, sampling is disabled and temperature is set to 0.0.
* Speculative decoding does not affect output quality. The output depends only on model weights and prompt.
* Speculative decoding generates multiple tokens at a time. Structured output (xgrammar, outlines) with state-machine guarantees (enforced json through `response_format`) isn't possible when lookahead decoding is enabled. Structured outputs are supported in standard Engine-Builder-LLM deployments without speculative decoding.
* Chunked prefill isn't supported with lookahead decoding. Baseten disables it automatically when lookahead is enabled.

## Configuration

### Basic lookahead configuration

Add a `speculator` section to your build configuration:

```yaml theme={"system"}
trt_llm:
  build:
    base_model: decoder
    checkpoint_repository:
      source: HF
      repo: "Qwen/Qwen2.5-7B-Instruct"
    speculator:
      speculative_decoding_mode: LOOKAHEAD_DECODING
      lookahead_windows_size: 3
      lookahead_ngram_size: 8
      lookahead_verification_set_size: 3
      enable_b10_lookahead: true
```

### Configuration parameters

**`speculative_decoding_mode`**: Set to `LOOKAHEAD_DECODING` to enable Baseten's lookahead decoding algorithm.

**`lookahead_ngram_size`**: Size of n-gram patterns for speculation. Minimum: 1, with no fixed maximum. Use `4` for simple patterns, `8` for general use (recommended), or `16-32` for complex, highly predictable patterns.

**`lookahead_verification_set_size`**: Size of the verification buffer for speculation. Minimum: 1. Use `1` for high-confidence patterns, `3` for general use (recommended), or `5` for complex patterns requiring more verification.

**`lookahead_windows_size`**: Size of the speculation window. Minimum: 1. Pair it with `lookahead_verification_set_size` for your workload, as in the examples below.

**`enable_b10_lookahead`**: Enable Baseten's optimized lookahead algorithm. Default: `false`. Set it to `true` to use Baseten's B10 lookahead, recommended for the configurations on this page.

### Performance tuning

**For coding agents:** Use smaller window sizes with moderate n-gram sizes:

```yaml theme={"system"}
speculator:
  speculative_decoding_mode: LOOKAHEAD_DECODING
  lookahead_windows_size: 1
  lookahead_ngram_size: 8
  lookahead_verification_set_size: 3
  enable_b10_lookahead: true
```

**For general text generation:** Use balanced window and n-gram sizes:

```yaml theme={"system"}
speculator:
  speculative_decoding_mode: LOOKAHEAD_DECODING
  lookahead_windows_size: 3
  lookahead_ngram_size: 8
  lookahead_verification_set_size: 3
  enable_b10_lookahead: true
```

**For highly predictable content:** Use larger n-gram sizes with conservative verification:

```yaml theme={"system"}
speculator:
  speculative_decoding_mode: LOOKAHEAD_DECODING
  lookahead_windows_size: 1
  lookahead_ngram_size: 32
  lookahead_verification_set_size: 1
  enable_b10_lookahead: true
```

## Performance impact

### Batch size considerations

Lookahead decoding performs best with smaller batch sizes. Set `max_batch_size` to 32 or 64, depending on your use case.

### Memory overhead

Lookahead decoding doesn't require additional GPU memory.

## Production best practices

### Recommended configurations

**Standard (general purpose):** Balanced settings for general-purpose text generation:

```yaml theme={"system"}
speculator:
  speculative_decoding_mode: LOOKAHEAD_DECODING
  lookahead_windows_size: 3
  lookahead_ngram_size: 8
  lookahead_verification_set_size: 3
  enable_b10_lookahead: true
```

**Dynamic content (less predictable):**

Setting `enable_b10_lookahead: true` and `lookahead_windows_size: 1 + lookahead_verification_set_size: 1` will enable dynamic length speculation.
The speculated length will depend on the quality of the lookup match. By default we will speculate "a n-gram of k tokens for a k token suffix match".

```yaml theme={"system"}
speculator:
  speculative_decoding_mode: LOOKAHEAD_DECODING
  lookahead_windows_size: 1
  lookahead_ngram_size: 32
  lookahead_verification_set_size: 1
  enable_b10_lookahead: true
```

**Code generation (highly predictable):** Code has predictable syntax patterns, so you can use larger windows:

```yaml theme={"system"}
speculator:
  speculative_decoding_mode: LOOKAHEAD_DECODING
  lookahead_windows_size: 7
  lookahead_ngram_size: 5
  lookahead_verification_set_size: 7
  enable_b10_lookahead: true
```

### Build configuration

Set `max_batch_size` to control batch size limits:

```yaml theme={"system"}
trt_llm:
  build:
    max_batch_size: 64  # Recommended for lookahead decoding
    speculator:
      speculative_decoding_mode: LOOKAHEAD_DECODING
      # ... other speculator config
```

### Engine optimization

* Use smaller batch sizes for maximum benefit (1-8 requests)
* Monitor memory overhead and adjust KV cache allocation
* Test with your specific workload for optimal parameters

## Examples

### Code generation example

Deploy a coding model with lookahead decoding on an H100:

```yaml theme={"system"}
model_name: Qwen-Coder-7B-Lookahead
resources:
  accelerator: H100
  cpu: '1'
  memory: 10Gi
  use_gpu: true
trt_llm:
  build:
    base_model: decoder
    checkpoint_repository:
      source: HF
      repo: "Qwen/Qwen2.5-7B-Instruct"
    quantization_type: fp8
    max_batch_size: 64
    speculator:
      speculative_decoding_mode: LOOKAHEAD_DECODING
      lookahead_windows_size: 1
      lookahead_ngram_size: 8
      lookahead_verification_set_size: 1
      enable_b10_lookahead: true
  runtime:
    served_model_name: "Qwen-Coder-7B"
```

### Python integration

Generate code using the chat completions API:

```python theme={"system"}
import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ['BASETEN_API_KEY'],
    base_url="https://model-xxxxxx.api.baseten.co/environments/production/sync/v1"
)

# Generate Python function refactor with lookahead decoding
code = "def hello_world(name):\n    print(42)"

response = client.chat.completions.create(
    model="not-required",
    messages=[
        {
            "role": "system", 
            "content": "You are a Python programming assistant. Write clean, efficient code."
        },
        {
            "role": "user", # By providing the code anywhere in the prompt, the generation is much faster.
            "content": f"Please refactor the following function to have docstrings. {code}"
        }
    ],
    temperature=0.0,
    max_tokens=200
)

print(response.choices[0].message.content)
```

## Monitoring and troubleshooting

### Performance monitoring

Track tokens/second with and without lookahead to measure speed improvement, verification accuracy to see how often speculations succeed, and memory usage to catch overhead. If speed improvement diminishes, reduce batch size. Adjust window size based on content predictability and ngram size based on verification accuracy.

### Troubleshooting

**Common issues:**

**Low speed improvement:**

* Check if content is suitable for lookahead decoding
* Reduce batch size for better performance
* Adjust window and ngram sizes

**Blackwell support**

* Lookahead isn't fully supported in Engine-Builder-LLM, check [BIS-LLM overview](/engines/bis-llm/overview) for Blackwell support.

## Deprecation: DRAFT\_TOKENS\_EXTERNAL mode

`DRAFT_TOKENS_EXTERNAL` (external draft speculation) is discontinued in favor of `LOOKAHEAD_DECODING`, which yields better performance. If you set `speculative_decoding_mode: DRAFT_TOKENS_EXTERNAL`, the build fails with an error directing you to switch.

For model-based speculation (Eagle, MTP), use [BIS-LLM speculative decoding](/engines/bis-llm/advanced-features#speculative-decoding) instead. These methods are not available on Engine-Builder-LLM.

## Related

* [Engine-Builder-LLM overview](/engines/engine-builder-llm/overview): Main engine documentation.
* [Engine-Builder-LLM configuration](/engines/engine-builder-llm/engine-builder-config): Complete reference config.
* [BIS-LLM speculative decoding](/engines/bis-llm/advanced-features#speculative-decoding): Eagle, MTP, and NGram on v2.
* [Structured outputs documentation](/inference/structured-outputs): JSON schema validation.
* [Examples section](/examples/speculative-decoding): Deployment examples.
