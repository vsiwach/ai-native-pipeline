# How Baseten works
Source: https://docs.baseten.co/concepts/howbasetenworks

The moving parts behind training, deployment, request routing, autoscaling, and environment promotion on Baseten.

Two paths get a model into production on Baseten: deploy an existing model with `truss push`, or train a new one and deploy from a checkpoint. This page covers the pieces that handle both paths: the build pipelines, request routing, autoscaling, cold starts, and environments. For the product surface and positioning, see the [overview](/overview) and [Why Baseten](/concepts/whybaseten).

## Multi-cloud Capacity Management (MCM)

Behind every GPU workload on Baseten is the Multi-cloud Capacity Management (MCM) system. MCM is the infrastructure control plane that unifies GPUs across cloud providers and geographic regions.

When you request a resource (an H100 in US-East-1 or a cluster of B200s in a private region), MCM provisions the hardware, configures networking, and monitors health. It abstracts the differences between cloud providers so the Baseten training and inference stack runs identically on any underlying infrastructure.

MCM also powers Baseten's high availability. Deployments run active-active across clusters and clouds, and if a region or provider faces a capacity crunch or outage, MCM re-routes and re-provisions workloads to maintain service continuity.

## Deploy an existing model

To deploy a model, package it with [Truss](https://pypi.org/project/truss/), Baseten's open-source model packaging tool. Describe the model in a `config.yaml` (for supported architectures) or a small Python `Model` class (for custom code), then run `truss push` to ship it.

<Steps>
  <Step title="Upload project">
    `truss push` validates your `config.yaml`, archives your project directory, and uploads it to cloud storage. Baseten receives the archive and starts the build.
  </Step>

  <Step title="Process model weights">
    For [Engine-Builder-LLM](/engines/engine-builder-llm/overview), Baseten downloads model weights from the source repository (Hugging Face, S3, or GCS) and compiles them with TensorRT-LLM. Compilation builds optimized CUDA kernels for the target GPU architecture, applies quantization if configured, and sets up tensor parallelism across multiple GPUs.
  </Step>

  <Step title="Package and deploy">
    Baseten packages the compiled engine, runtime configuration, and serving infrastructure into a container, deploys it to GPU infrastructure, and exposes it as an API endpoint.
  </Step>
</Steps>

`truss push` returns once the upload finishes. For engine-based deployments, compilation can take several minutes. Watch progress in the deployment logs, or wait for the dashboard to show "Active."

For [custom model code](/development/model/model-class) deployments, the build is faster: Baseten installs your Python dependencies, packages your `Model` class into a container, and deploys it. Inference optimization is on you in custom builds.

Each push produces a container image identified by a content hash and stored in Baseten's container registry. The image is immutable, and an unchanged project reuses the cached image instead of triggering a new build.

## Train a model

To train a model, define the training job in a Python config and submit it with `truss train push`. Baseten provisions GPUs through MCM, runs your training container, and syncs checkpoints to storage as the job progresses.

<Steps>
  <Step title="Submit the job">
    `truss train push config.py` packages your training config, uploads it to Baseten, and starts the job on the hardware you specified (H100 or H200, single-node or multi-node). Your training code can use Axolotl, TRL, VeRL, Megatron, or any other framework you bundle into the container.
  </Step>

  <Step title="Run and checkpoint">
    Baseten runs your training container on the provisioned GPUs. As your training code writes checkpoints to the configured directory, Baseten uploads them to durable storage. If the job fails or you stop it, the most recent checkpoint is still available.
  </Step>

  <Step title="Deploy from checkpoint">
    `truss train deploy_checkpoints --job-id <job_id>` constructs a Truss `config.yaml` from the checkpoint, packages it as a deployment, and exposes an API endpoint. From there, the deployment behaves like any other model on Baseten.
  </Step>
</Steps>

For a fully managed training path with Tinker-compatible Python, see [Loops](/loops/overview). For the full training lifecycle, see [Training overview](/training/overview).

## Request routing

Each deployment gets a dedicated subdomain: `https://model-{model_id}.api.baseten.co/`. The URL path determines which deployment handles the request. Requests to `/production/predict` go to the production environment, `/development/predict` goes to the development deployment, and you can also target a specific deployment by ID or a custom environment by name.

From the URL path, Baseten resolves the environment and routes the request to an active replica. If the deployment has scaled to zero, Baseten starts a replica and parks the request until the model loads. The caller receives the response regardless of whether the model was warm or cold-started.

Engine-based deployments serve an [OpenAI-compatible API](/reference/inference-api/chat-completions) at the `/v1/chat/completions` path, so any code written for the OpenAI SDK works without modification. Custom model deployments use the [predict API](/reference/inference-api/overview), which accepts and returns arbitrary JSON.

For long-running workloads, [async requests](/inference/async) return a request ID immediately. The request enters a queue managed by an async request service. A background worker then calls your model and delivers the result through a webhook. Sync requests get priority when capacity is tight, so background work doesn't starve real-time traffic.

## Autoscaling

Baseten's autoscaler matches replica count to in-flight request load, keeping each replica below its [concurrency target](/deployment/autoscaling/overview).

Scale-up is immediate. When the average load over the autoscaling window (default 60 seconds) crosses the target utilization (default 70%), the autoscaler adds replicas, up to the configured maximum.

Scale-down is deliberate. When load drops, the autoscaler waits one `scale_down_delay` (default 900 seconds), then halves the excess replicas. The timer resets, and the cycle repeats until the deployment reaches its target size. This staircase pattern prevents thrashing when traffic briefly dips and recovers.

Set [`min_replica`](/deployment/autoscaling/overview) to 0 for scale-to-zero: the deployment incurs no GPU cost when idle, but the next request triggers a cold start. Set `min_replica` to 1 or higher to keep warm capacity ready, trading cost for lower latency.

## Cold starts and the Baseten Delivery Network

The slowest part of a cold start is loading model weights, which can reach hundreds of gigabytes. Baseten addresses this with the [Baseten Delivery Network (BDN)](/development/model/bdn), a multi-tier caching system for model weights.

When you first deploy, BDN mirrors your model weights from the source repository to Baseten's own blob storage. After that, no cold start depends on an upstream service like Hugging Face or S3. When a new replica starts, the BDN agent on the node fetches a manifest for the weights, downloads them through an in-cluster cache (shared across all replicas in the cluster), and stores them in a node-level cache (shared across replicas on the same node). Identical files across different models are deduplicated, so a fine-tune that shares most weights with the base model only downloads the delta.

Subsequent cold starts on the same node or in the same cluster are significantly faster than the first. Container images use streaming, so the model begins loading weights before the image download completes.

BDN serves training jobs the same way. Mount weights and training data into your training container from any supported source, and BDN caches them so subsequent jobs start faster.

## Environments and promotion

Every model starts as a development deployment with scale-to-zero and live reload, configured for fast iteration. When the model is ready for production traffic, promote it to a named [environment](/deployment/environments) like production, staging, or canary.

Each environment has its own stable URL, autoscaling settings, and metrics. Promoting a new deployment swaps it in for the previous one and inherits the environment's autoscaling settings. The endpoint URL stays constant when you promote, so your application code doesn't need to change. Baseten demotes the previous deployment and scales it to zero, so you can roll back by re-promoting it.

Promotion reuses the image the deployment was already built with, so it never rebuilds or re-pulls your base image. Rollback works the same way: re-promoting a previous deployment reuses its existing image.

To skip the development stage, push directly to an environment with `truss push --environment staging`. Only one promotion can be active per environment at a time, which prevents conflicting updates. See [Deployment concepts](/deployment/concepts) for the full set of resource and CI/CD options.

These pieces work the same whether you deploy an existing model or train a new one, so the path from prototype to production stays consistent.

## Next steps

<CardGroup>
  <Card title="Deploy your first model" icon="cube" href="/development/model/build-your-first-model">
    Package a model with Truss and deploy it with a single config file.
  </Card>

  <Card title="Training overview" icon="dumbbell" href="/training/overview">
    Run a fine-tune or pre-train and deploy the checkpoint to an endpoint.
  </Card>
</CardGroup>
