# Baseten overview
Source: https://docs.baseten.co/overview

Baseten helps you train, deploy, and serve AI models at scale with high performance and cost efficiency.

Baseten is a training and inference platform.
Bring a model (an open-source LLM from Hugging Face, a fine-tuned checkpoint, or a custom model) and Baseten turns it into a production API endpoint with autoscaling, observability, and optimized serving infrastructure.
Baseten handles containerization, GPU scheduling across multiple clouds, and engine-level optimizations like TensorRT-LLM compilation, so you can focus on your model and your application.

If you want to skip deployment entirely and start making inference calls right now, [Model APIs](/inference/model-apis/overview) provide OpenAI-compatible endpoints for models like DeepSeek, Qwen, and GLM.
Point the OpenAI SDK at Baseten's URL to run inference in seconds.

If you're an AI lab serving your own hosted model to your own customers under a branded URL with federated keys and per-customer billing, [Frontier Gateway](/frontier-gateway/overview) is the managed gateway product for that.

<Card title="Quickstart: Make your first inference call" icon="rocket" href="/quickstart">
  Call a model through Model APIs in under two minutes. No deployment, no setup, just an API key and a request.
</Card>

## Deploy a model

The most common way to deploy a model on Baseten is with [Truss](https://pypi.org/project/truss/), an open-source framework that packages your model into a deployable container.
For supported architectures (most popular open-source LLMs, embedding models, and image generators), you only need a `config.yaml` file.
Specify the model, the hardware, and the engine, and Truss handles the rest.

```yaml config.yaml theme={"system"}
model_name: Qwen-2.5-3B
resources:
  accelerator: L4
trt_llm:
  build:
    base_model: decoder
    checkpoint_repository:
      source: HF
      repo: "Qwen/Qwen2.5-3B-Instruct"
```

Run `truss push` and Baseten builds a TensorRT-optimized container, deploys it to GPU infrastructure, and provides an endpoint.
The model serves an OpenAI-compatible API out of the box.

When you need custom behavior like preprocessing, postprocessing, or a model architecture that the built-in engines don't support, Truss also supports [custom Python model code](/development/model/model-class).
Write a `Model` class with `load` and `predict` methods, and Truss packages it the same way.
Most teams start with config-only deployments and add custom code only when they need it.

<Card title="Your first model" icon="cube" href="/development/model/build-your-first-model">
  Deploy a model to Baseten with just a config file. No custom code needed.
</Card>

## Inference engines

Baseten optimizes every deployment with an inference engine tuned for your model's architecture. Select the engine that best supports your use case, and it handles the low-level performance work: quantization, tensor parallelism, KV cache management, and batching.

<CardGroup>
  <Card title="Engine-Builder-LLM" icon="microchip" href="/engines/engine-builder-llm/overview">
    Dense text generation models compiled with TensorRT-LLM. Supports lookahead decoding and structured outputs.
  </Card>

  <Card title="BIS-LLM" icon="network-wired" href="/engines/bis-llm/overview">
    Large mixture-of-experts models like DeepSeek R1 and Qwen3 MoE with KV-aware routing and distributed inference.
  </Card>

  <Card title="BEI" icon="bolt" href="/engines/bei/overview">
    Embedding, reranking, and classification models with up to 1,400 client embeddings per second.
  </Card>
</CardGroup>

Choose the engine through a field in your `config.yaml`, or Baseten selects it automatically based on your model architecture.

## Multi-step workflows with Chains

Some applications need more than a single model call. A RAG pipeline retrieves documents, embeds them, and generates a response. An image generation workflow runs a diffusion model, upscales the result, and applies safety filtering.

[Chains](/development/chain/overview) is Baseten's framework for orchestrating these multi-step pipelines. Each step runs on its own hardware with its own dependencies, and Chains manages the data flow between them. Define the pipeline in Python, and Chains deploys, scales, and monitors each step independently.

## Training

Baseten also provides [training infrastructure](/training/overview) for fine-tuning and pre-training. Bring your training scripts (Axolotl, TRL, Megatron, or custom code) and run jobs on H200 or H100 GPUs. Checkpoints sync automatically during training, and you can deploy a fine-tuned model from checkpoint to production endpoint in a single command with `truss train deploy_checkpoints`.

## Production infrastructure

Every deployment on Baseten runs on autoscaling infrastructure that adjusts replicas based on traffic. Configure minimum and maximum replicas, concurrency targets, and scale-down delays. Or use the defaults, which handle most workloads well. Models scale to zero when idle, eliminating costs during quiet periods, and scale up within seconds when traffic arrives.

Baseten schedules workloads across multiple cloud providers and regions through Multi-cloud Capacity Management (MCM). Your models stay available even during provider-level disruptions, and MCM routes traffic across regions to minimize latency.

Built-in [observability](/observability/metrics) gives you real-time metrics, logs, and request traces for every deployment. Export data to tools like Datadog or Prometheus, and debug behavior with full visibility into inputs, outputs, and errors.

## Find your path

<Tabs>
  <Tab title="Build AI applications">
    Start with Model APIs and explore features that support production use cases.

    * [Model APIs overview](/inference/model-apis/overview)
    * [Structured outputs](/inference/structured-outputs)
    * [Tool calling](/inference/function-calling)
    * [RAG pipeline example](/examples/chains-build-rag)
  </Tab>

  <Tab title="Deploy and optimize models">
    Deploy models on dedicated infrastructure with a config-only Truss deployment and tune from there.

    * [Deploy your first model](/development/model/build-your-first-model)
    * [Engine selection](/engines)
    * [Autoscaling](/deployment/autoscaling/overview)
    * [Performance optimization](/development/model/performance-optimization)
  </Tab>

  <Tab title="Train and fine-tune">
    Run training jobs and deploy results directly to production endpoints.

    * [Training overview](/training/overview)
    * [Get started with training](/training/getting-started)
    * [Deploy from checkpoint](/training/deployment)
  </Tab>
</Tabs>

## Next steps

<CardGroup>
  <Card title="How Baseten works" icon="gears" href="/concepts/howbasetenworks">
    The build pipeline, request routing, autoscaling, and deployment lifecycle under the hood.
  </Card>

  <Card title="Examples" icon="book-open" href="/examples/overview">
    End-to-end guides for deploying and optimizing popular models.
  </Card>

  <Card title="API reference" icon="code" href="/reference/overview#api-reference">
    Reference for the inference API, management API, and Truss CLI.
  </Card>
</CardGroup>
