# Deploy a Dockerized model
Source: https://docs.baseten.co/examples/docker

Deploy any model in a pre-built Docker container.

<Card title="View on GitHub" icon="github" href="https://github.com/basetenlabs/truss-examples/tree/main/custom-server/infinity-embedding-server" />

In this example, we deploy a dockerized model for [infinity embedding server](https://github.com/michaelfeil/infinity), a high-throughput, low-latency REST API server for serving vector embeddings.

# Set up the `config.yaml`

To deploy a dockerized model, all you need is a `config.yaml`. It specifies how to build your Docker image, start the server, and manage resources. Let’s break down each section.

## Base image

Sets the foundational Docker image to a lightweight Python 3.11 environment.

```yaml config.yaml theme={"system"}
base_image:
  image: python:3.11-slim
```

## Docker server configuration

Configures the server's startup command, health check endpoints, prediction endpoint, and the port on which the server will run.

```yaml config.yaml theme={"system"}
docker_server:
  start_command: sh -c "HF_TOKEN=$(cat /secrets/hf_access_token) infinity_emb v2 --batch-size 64 --model-id BAAI/bge-small-en-v1.5 --revision main"
  readiness_endpoint: /health
  liveness_endpoint: /health
  predict_endpoint: /embeddings
  server_port: 7997
```

## Build commands (optional)

Pre-downloads model weights during the build phase to ensure the model is ready at container startup.

```yaml config.yaml theme={"system"}
build_commands: # optional step to download the weights of the model into the image
  - sh -c "HF_TOKEN=$(cat /secrets/hf_access_token) infinity_emb v2 --preload-only --no-model-warmup --model-id BAAI/bge-small-en-v1.5 --revision main"
```

## Configure resources

Note that we need an L4 to run this model.

```yaml config.yaml theme={"system"}
resources:
  accelerator: L4
  use_gpu: true
```

## Requirements

Lists the Python package dependencies required for the infinity embedding server.

```yaml config.yaml theme={"system"}
requirements:
  - infinity-emb[all]==0.0.77
```

## Runtime settings

Sets the server to handle up to 40 concurrent inferences to manage load efficiently.

```yaml config.yaml theme={"system"}
runtime:
  predict_concurrency: 40
```

## Environment variables

Defines essential environment variables including the Hugging Face access token, request batch size, queue size limit, and a flag to disable tracking.

```yaml config.yaml theme={"system"}
environment_variables:
  hf_access_token: null
  # constrain api to at most 256 sentences per request, for better load-balancing
  INFINITY_MAX_CLIENT_BATCH_SIZE: 256
  # constrain model to a max backpressure of INFINITY_MAX_CLIENT_BATCH_SIZE * predict_concurrency = 10241 requests
  INFINITY_QUEUE_SIZE: 10241
  DO_NOT_TRACK: 1
```

# Deploy dockerized model

Deploy the model like you would other Trusses, with:

```bash theme={"system"}
truss push infinity-embedding-server
```

<Note>
  `docker_server` configs deploy as published deployments and don't support development mode. Using `truss push --watch` with a `docker_server` config returns an error. Use `truss push` without `--watch` to deploy to production.
</Note>
