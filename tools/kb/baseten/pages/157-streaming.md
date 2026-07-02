# Streaming
Source: https://docs.baseten.co/inference/streaming

Return model output token by token as it is generated.

Streaming refers to returning a model's output incrementally, token by token, as it is generated, rather than holding the response until generation finishes. The caller reads the output as it builds, so the first tokens arrive after the time to first token (TTFT) instead of after the entire response.

Baseten supports streaming across a range of inference surfaces: [Model APIs](/inference/model-apis/overview) (hosted, OpenAI- and Anthropic-compatible endpoints), [BIS-LLM](/engines/bis-llm/overview), and dedicated deployments of models packaged with [Truss](/development/model/overview). [Custom Docker containers](/development/model/custom-server) that expose an OpenAI-compatible API, such as vLLM and SGLang, stream the same way.

Use streaming when:

* Generating the complete output takes a relatively long time.
* The first tokens are useful without the rest of the output.
* Reducing the time to first token improves the user experience.

Chat applications backed by LLMs are the clearest example.

## Enable streaming

Streaming is a per-request flag: set it on your call, then read the response as it arrives. The flag is the same everywhere; only the base URL and model slug differ.

<CodeGroup>
  ```python Truss theme={"system"}
  # Self-deployed Truss model: stream from the model's predict endpoint
  import os
  import requests

  model_id = "YOUR_MODEL_ID"

  with requests.post(
      f"https://model-{model_id}.api.baseten.co/production/predict",
      headers={"Authorization": f"Bearer {os.environ['BASETEN_API_KEY']}"},
      json={"prompt": "Write a haiku about the ocean.", "stream": True},
      stream=True,
  ) as resp:
      for chunk in resp.iter_content():
          print(chunk.decode("utf-8"), end="", flush=True)
  ```

  ```python OpenAI theme={"system"}
  # Model APIs: OpenAI-compatible endpoint at inference.baseten.co
  import os
  from openai import OpenAI

  client = OpenAI(
      base_url="https://inference.baseten.co/v1",
      api_key=os.environ["BASETEN_API_KEY"],
  )

  stream = client.chat.completions.create(
      model="deepseek-ai/DeepSeek-V4-Pro",
      messages=[{"role": "user", "content": "Write a haiku about the ocean."}],
      stream=True,
  )
  for chunk in stream:
      print(chunk.choices[0].delta.content or "", end="", flush=True)
  ```

  ```python Anthropic theme={"system"}
  # Model APIs: Anthropic-compatible endpoint (beta) at inference.baseten.co
  import os
  import anthropic

  api_key = os.environ["BASETEN_API_KEY"]

  client = anthropic.Anthropic(
      base_url="https://inference.baseten.co",
      api_key=api_key,
      default_headers={"Authorization": f"Bearer {api_key}"},
  )

  with client.messages.stream(
      model="deepseek-ai/DeepSeek-V4-Pro",
      max_tokens=4096,
      messages=[{"role": "user", "content": "Write a haiku about the ocean."}],
  ) as stream:
      for text in stream.text_stream:
          print(text, end="", flush=True)
  ```

  ```bash cURL theme={"system"}
  # Model APIs: add "stream": true and keep the connection open with --no-buffer
  curl https://inference.baseten.co/v1/chat/completions \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $BASETEN_API_KEY" \
    -d '{
      "model": "deepseek-ai/DeepSeek-V4-Pro",
      "messages": [{"role": "user", "content": "Write a haiku about the ocean."}],
      "stream": true
    }' \
    --no-buffer
  ```
</CodeGroup>

Streaming changes when the caller sees output, not how much the model produces. The following diagram puts both delivery modes on one clock.

<MiniStreaming />

The top lane streams: after a short prefill, tokens fill in one at a time from the first-token mark (TTFT). The bottom lane is non-streaming: it stays empty through the same generation, then the whole response lands at once at the end. Both finish together, so the only difference is when the caller first sees output. Token timing here is illustrative, not a measured latency.
