# gRPC
Source: https://docs.baseten.co/development/model/grpc

Invoke your model over gRPC.

gRPC is a high-performance, open-source remote procedure call (RPC) framework that uses HTTP/2 for transport and Protocol Buffers for serialization. Unlike traditional HTTP APIs, gRPC provides strong type safety, high performance, and built-in support for streaming and bidirectional communication. Run a gRPC server on Baseten when you want these properties for model inference.

gRPC offers:

* **Type safety**: Protocol Buffers enforce strong typing and contract validation between client and server.
* **Ecosystem integration**: Integrate Baseten with existing gRPC-based services.
* **Streaming support**: Built-in server streaming, client streaming, and bidirectional streaming.
* **Language interoperability**: Generate client libraries for multiple programming languages from a single `.proto` file.

## gRPC on Baseten

gRPC models run as [custom servers](/development/model/custom-server). Your own server process handles gRPC requests directly, instead of going through the standard Truss `load()` and `predict()` methods.

For this to work, you must first package your gRPC server code into a Docker image.
Once that is done, you can set up your Truss `config.yaml` to configure your deployment
and push the server to Baseten.

## Setup

### Installation

1. **Install [uv](https://docs.astral.sh/uv/)** if you don't have it. This guide uses `uvx` to run [Truss](https://pypi.org/project/truss/) commands without a separate install step.

2. **Install Protocol Buffer compiler:**
   ```bash Terminal theme={"system"}
   # On macOS
   brew install protobuf

   # On Ubuntu/Debian
   sudo apt-get install protobuf-compiler

   # On other systems, see: https://protobuf.dev/getting-started/
   ```

3. **Set up a virtual environment and install gRPC tools:**
   ```bash Terminal theme={"system"}
   uv venv && source .venv/bin/activate
   uv pip install grpcio-tools
   ```

### Protocol buffer definition

Your gRPC service starts with a `.proto` file that defines the service interface and message types. Create an `example.proto` file in your project root:

```protobuf example.proto theme={"system"}
syntax = "proto3";

package example;

// The greeting service definition
service Greeter {
  // Sends a greeting
  rpc SayHello (HelloRequest) returns (HelloReply) {}
}

// The request message containing the user's name
message HelloRequest {
  string name = 1;
}

// The response message containing the greeting
message HelloReply {
  string message = 1;
}
```

#### Generate Protocol Buffer code

Generate the Python code from your `.proto` file:

```bash Terminal theme={"system"}
python -m grpc_tools.protoc --python_out=. --grpc_python_out=. --proto_path . example.proto
```

This generates the necessary Python files (`example_pb2.py` and `example_pb2_grpc.py`) for your gRPC service. For more information about Protocol Buffers, see the [official documentation](https://protobuf.dev/).

### Model implementation

Create your gRPC server implementation in a file called `model.py`. Here's a basic example:

```python model.py theme={"system"}
import grpc
from concurrent import futures
import time
import example_pb2
import example_pb2_grpc

from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc
from grpc_health.v1.health import HealthServicer


class GreeterServicer(example_pb2_grpc.GreeterServicer):
    def SayHello(self, request, context):
        response = example_pb2.HelloReply()
        response.message = f"Hello, {request.name}!"
        return response


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    example_pb2_grpc.add_GreeterServicer_to_server(GreeterServicer(), server)

    # The gRPC health check service must be used in order for Baseten
    # to consider the gRPC server healthy.
    health_servicer = HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    health_servicer.set(
        "example.GreeterService", health_pb2.HealthCheckResponse.SERVING
    )

    # Ensure the server runs on port 50051
    server.add_insecure_port("[::]:50051")

    server.start()
    print("gRPC server started on port 50051")

    # Keep the server running
    try:
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        print("Shutting down server...")
        server.stop(0)


if __name__ == "__main__":
    serve()
```

## Deployment

### Create a Dockerfile

Since gRPC on Baseten requires a custom server setup, you'll need to create a `Dockerfile` that bundles your gRPC server code and dependencies. Here's a basic skeleton:

```dockerfile Dockerfile theme={"system"}
FROM debian:latest

RUN apt-get update && apt-get install -y \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN python3 -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY model.py ./model.py
COPY example_pb2.py example_pb2_grpc.py ./

EXPOSE 8080

CMD ["python", "model.py"]

```

Create a `requirements.txt` file with your gRPC dependencies:

```txt requirements.txt theme={"system"}
grpcio
grpcio-health-checking
grpcio-tools
protobuf
```

### Build and push Docker image

Build and push your Docker image to a container registry:

```bash Terminal theme={"system"}
docker build -t your-registry/truss-grpc-demo:latest . --platform linux/amd64
docker push your-registry/truss-grpc-demo:latest
```

<Tip>
  Replace `your-registry` with your actual container registry (for example, Docker Hub, Google Container Registry, AWS ECR). You can create a Docker Hub container registry by [following their documentation](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-registry/#try-it-out).
</Tip>

### Configure your Truss

Update your `config.yaml` to use the custom Docker image and configure the gRPC server:

```yaml config.yaml theme={"system"}
model_name: "gRPC Model Example"
base_image:
  image: your-registry/truss-grpc-demo:latest
docker_server:
  start_command: python model.py
  # 50051 is the only supported server port.
  server_port: 50051
  # The _endpoint fields are ignored for gRPC models.
  predict_endpoint: /
  readiness_endpoint: /
  liveness_endpoint: /
resources:
  accelerator: L4  # or your preferred GPU
  use_gpu: true
runtime:
  transport:
    kind: "grpc"
```

### Deploy with Truss

Deploy your model using the Truss CLI. gRPC models aren't supported in development deployments, so use the default published deployment or `--promote` to also promote to production.

```bash Terminal theme={"system"}
uvx truss push --promote
```

For more detailed information about Truss deployment, see the [truss push documentation](/reference/cli/truss/push).

## Call your model

### Use a gRPC client

Once deployed, you can call your model using any gRPC client. Here's an example Python client:

```python client.py theme={"system"}
import grpc
import example_pb2
import example_pb2_grpc


def run():
    channel = grpc.secure_channel(
        "model-{MODEL_ID}.grpc.api.baseten.co:443",
        grpc.ssl_channel_credentials(),
    )

    stub = example_pb2_grpc.GreeterStub(channel)

    request = example_pb2.HelloRequest(name="World")

    metadata = [
        ("baseten-authorization", "Api-Key {API_KEY}"),
        ("baseten-model-id", "model-{MODEL_ID}"),
    ]

    response = stub.SayHello(request, metadata=metadata)
    print(response.message)


if __name__ == "__main__":
    run()


```

### Inference for specific environments and deployments

To target a specific environment or deployment, add the corresponding header to your `metadata` list:

```python client.py theme={"system"}
metadata = [
    ('baseten-authorization', 'Api-Key {API_KEY}'),
    ('baseten-model-id', 'model-{MODEL_ID}'),
    # To target a specific environment:
    ('x-baseten-environment', 'staging'),
    # Or, to target a specific deployment instead:
    # ('x-baseten-deployment', 'your-deployment-id'),
]
```

### Inference for regional environments

If your organization uses [regional environments](/deployment/environments#regional-environments), use the regional hostname as the gRPC target. The environment is derived from the hostname, so do not set `x-baseten-environment` or `x-baseten-deployment` headers.

```python client.py theme={"system"}
channel = grpc.secure_channel(
    "model-{MODEL_ID}-{ENV_NAME}.grpc.api.baseten.co:443",
    grpc.ssl_channel_credentials(),
)

metadata = [
    ('baseten-authorization', 'Api-Key {API_KEY}'),
    ('baseten-model-id', 'model-{MODEL_ID}'),
]
```

### Test your deployment

Run your client to test the deployed model:

```bash Terminal theme={"system"}
python client.py
```

## Per-request logging

Baseten assigns a unique request ID to every predict call and returns it in the `x-baseten-request-id` response metadata. You can use this ID to [filter your model's logs](/observability/logs) down to a single request.

For standard Truss models, request ID logging is automatic. For custom gRPC servers, you'll need to extract the request ID from the incoming metadata and include it in your JSON log output.

Extract the request ID from the `x-baseten-request-id` metadata key:

```python model.py theme={"system"}
import json
import logging
import sys

import example_pb2
import example_pb2_grpc


class JSONFormatter(logging.Formatter):
    """Formats logs as JSON with request_id for Baseten log filtering."""

    def format(self, record):
        log_record = {
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if getattr(record, "request_id", None):
            log_record["request_id"] = record.request_id
        return json.dumps(log_record)


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JSONFormatter())
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


class GreeterServicer(example_pb2_grpc.GreeterServicer):
    def SayHello(self, request, context):
        metadata = dict(context.invocation_metadata())
        request_id = metadata.get("x-baseten-request-id")

        logger.info(
            f"Received greeting request for {request.name}",
            extra={"request_id": request_id},
        )

        response = example_pb2.HelloReply()
        response.message = f"Hello, {request.name}!"

        logger.info("Request complete", extra={"request_id": request_id})
        return response
```

<Note>
  Logs must be JSON formatted and written to stdout. The `request_id` field must be a top-level key in the JSON object.
</Note>

## Full example

See this [GitHub repository](https://github.com/basetenlabs/truss-examples/tree/main/grpc) for a full example.

## Scaling

While many gRPC requests follow the traditional request-response pattern, gRPC also supports
bidirectional streaming and long-lived connections. The implication of this is that
a single long-lived connection, even if no data is being sent, counts
against the concurrency target for the deployment.

## Promotion

Like HTTP deployments, you can promote a gRPC deployment to an environment through the REST API or UI.

When you promote a gRPC deployment, new connections are routed to the new deployment, but existing
connections stay on the current deployment until they terminate.
Depending on the length of the connection, old deployments can take longer to scale down
than HTTP deployments.

## Monitoring

As with HTTP deployments, Baseten exposes performance metrics for gRPC deployments.

### Inference volume

Baseten tracks inference volume as the number of RPCs per minute. The platform publishes these metrics *after* the request completes.

See [gRPC status codes](https://grpc.io/docs/guides/status-codes/) for a full list
of codes.

### End-to-end response time

Measured at different percentiles (p50, p90, p95, p99):

End-to-end response time includes cold starts, queuing, and inference (excludes client-side latency). Reflects real-world performance.

## Next steps

* [Custom servers](/development/model/custom-server): Configure `docker_server` and `no_build` for container-based deployments.
* [truss push](/reference/cli/truss/push): Deploy and promote your gRPC model.
* [WebSockets](/development/model/websockets): Another transport for real-time, bidirectional communication.
