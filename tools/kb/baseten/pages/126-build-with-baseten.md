# Build with Baseten
Source: https://docs.baseten.co/examples/overview



These examples walk through common ways to deploy and serve models on Baseten. Each section below covers a different packaging approach, so pick whichever fits your model and workflow. If you're new to Baseten, start with [Deploy your first model](/examples/deploy-your-first-model).

## Engines

Config-only deploys on Baseten's optimized inference engines. This is the fastest path for LLMs, embeddings, and other common architectures, with no Python or Dockerfile required. See [engines](/engines) for architecture support, quantization options, and performance guidance.

<CardGroup>
  <Card title="Fast LLMs with TensorRT-LLM" href="/examples/tensorrt-llm" />

  <Card title="Speculative decoding" href="/examples/speculative-decoding" />

  <Card title="Embeddings with BEI" href="/examples/bei" />
</CardGroup>

## Custom Docker servers

Bring your own inference server, such as vLLM, SGLang, or anything that speaks HTTP. Baseten runs the container, and you own the serving stack. See [Docker server](/development/model/custom-server) for configuration.

<CardGroup>
  <Card title="Deploy a Hugging Face model" href="/examples/deploy-a-hugging-face-model" />

  <Card title="Run any LLM with vLLM" href="/examples/vllm" />

  <Card title="Deploy LLMs with SGLang" href="/examples/sglang" />

  <Card title="Deploy LLMs with Ollama" href="/examples/ollama" />

  <Card title="Dockerized model" href="/examples/docker" />
</CardGroup>

## Custom Python models

Write the Truss `Model` class for full control over load and predict. Use when no engine or open-source server fits your architecture. See [custom model code](/development/model/model-class) for the API.

<CardGroup>
  <Card title="Build and deploy a LLM" href="/examples/deploy-a-llm" />

  <Card title="Image generation" href="/examples/image-generation" />

  <Card title="Customize a model" href="/examples/customize-a-model" />
</CardGroup>

## Chains

Compose multi-step AI workflows across models, routing, parallelism, and post-processing. See [Chains](/development/chain/overview) for the SDK.

<CardGroup>
  <Card title="RAG pipeline with Chains" href="/examples/chains-build-rag" />

  <Card title="Transcribe audio with Chains" href="/examples/chains-audio-transcription" />
</CardGroup>

## Training

Train and fine-tune models with Baseten's scalable training infrastructure. From [fine-tuning large language models](/training/getting-started) to training custom models, our platform provides the tools and compute you need.

<CardGroup>
  <OpenAIIconCard title="GPT OSS 20B with LoRA" href="https://github.com/basetenlabs/ml-cookbook/tree/main/examples/oss-gpt-20b-axolotl/training" />

  <QwenIconCard title="Qwen3 8B LoRA DPO" href="https://github.com/basetenlabs/ml-cookbook/tree/main/examples/qwen3-8b-lora-dpo-trl" />

  <QwenIconCard title="Long Context Qwen3-30B" href="https://github.com/basetenlabs/ml-cookbook/tree/main/recipes/sft/long_context" />

  <QwenIconCard title="Coding with Qwen3-8B" href="https://github.com/basetenlabs/ml-cookbook/tree/main/recipes/rl/ocaml_specialist" />
</CardGroup>

Our training infrastructure supports popular frameworks including VERL, Megatron, and Unsloth, as well as models trained directly with Hugging Face Transformers.
