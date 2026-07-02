# Custom Docker containers
Source: https://docs.baseten.co/development/model/custom-server

Deploy custom Docker containers to run inference servers like vLLM, SGLang, Triton, or any containerized application.

By default, Truss wraps your `Model` class with the [Truss server base image](https://hub.docker.com/r/baseten/truss-server-base/tags). To deploy a pre-built container instead (vLLM, SGLang, Triton, NIM, or your own), point Truss at the image and tell it how to run.

## How the build works

When you deploy a standard custom server, Baseten builds a new image from your `base_image`: it layers in the reverse proxy and process supervisor, validates that the base image is [Debian-based with Python on `PATH`](#base-image-requirements), and pushes the result to its container registry. Your server runs behind that proxy, which is why [port 8080 is reserved](#runtime-environment) and [containers run as a non-root user](#non-root-user). To run your image unmodified instead, use [no-build](#no-build-deployment).

## Configure a custom container

Set [`base_image`](/reference/truss-configuration#base-image-image) to your image and use `docker_server` to specify how to start it:

```yaml config.yaml theme={"system"}
base_image:
  image: your-registry/your-image:latest
docker_server:
  start_command: your-server-start-command
  server_port: 8000
  predict_endpoint: /predict
  readiness_endpoint: /health
  liveness_endpoint: /health
```

* `image`: The Docker image to use.
* `start_command`: The command to start the server. This overrides the base image's default entrypoint.
* `server_port`: The port to listen on.
* `predict_endpoint`: The endpoint to forward requests to.
* `readiness_endpoint`: The endpoint to check if the server is ready.
* `liveness_endpoint`: The endpoint to check if the server is alive.

<Warning>
  Port 8080 is reserved by Baseten's internal reverse proxy. If your server binds to port 8080, the deployment fails with `[Errno 98] address already in use`.
</Warning>

For the full list of fields, see the
[configuration reference](/reference/truss-configuration#docker_server).

### Non-root user

Containers run as a non-root user by default:

| Property       | Value       |
| -------------- | ----------- |
| Username       | `app`       |
| UID / GID      | `60000`     |
| Home directory | `/home/app` |

If your base image expects a specific non-root UID, set `run_as_user_id` under `docker_server`:

```yaml config.yaml theme={"system"}
base_image:
  image: your-registry/your-image:latest
docker_server:
  start_command: your-server-start-command
  server_port: 8000
  predict_endpoint: /predict
  readiness_endpoint: /health
  liveness_endpoint: /health
  run_as_user_id: 1000
```

The UID must already exist in the base image. Values `0` (root) and `60000` (platform default) are not allowed.

<Note>
  Many NVIDIA base images, including NIM and Triton, run as user ID `1000`. Set `run_as_user_id: 1000` when using these images.
</Note>

Baseten automatically sets ownership of `/app`, `/workspace`, the packages directory, and `$HOME` to this UID. If your server writes to directories outside of these, ensure they are writable by the specified UID in your base image or through `build_commands`.

<Accordion title="Endpoint mapping">
  While `predict_endpoint` maps your server's inference route to Baseten's
  `/predict` endpoint, you can access any route exposed by your server using the
  [sync endpoint](/inference/calling-your-model#sync-api-endpoints).

  | Baseten endpoint                            | Maps to                       |
  | ------------------------------------------- | ----------------------------- |
  | `/environments/production/predict`          | Your `predict_endpoint` route |
  | `/environments/production/sync/{any/route}` | `/{any/route}` in your server |

  **Example:** If you set `predict_endpoint: /v1/chat/completions`:

  | Baseten endpoint                          | Maps to                |
  | ----------------------------------------- | ---------------------- |
  | `/environments/production/predict`        | `/v1/chat/completions` |
  | `/environments/production/sync/v1/models` | `/v1/models`           |

  All other paths reach your server unchanged, including routes like `/metrics` and `/health`. If your server doesn't handle a requested path, the reverse proxy returns whatever response your server returns (often its own 404).
</Accordion>

## Container filesystem

### Writable directories

Your server process can write to these paths:

| Path         | Purpose                                                             |
| ------------ | ------------------------------------------------------------------- |
| `/app`       | Application root, including your `config.yaml` and optional `data/` |
| `/home/app`  | Home directory (`$HOME`)                                            |
| `/tmp`       | Temporary files                                                     |
| `/workspace` | General-purpose scratch space                                       |
| `/packages`  | Bundled [packages](/development/model/dependencies#python-packages) |

Paths outside this list are root-owned and not writable by your process. If you need to write elsewhere, change permissions during the build with `build_commands`, or set `run_as_user_id` so Baseten chowns the managed paths to your UID.

### Working directory

Truss does not set a `WORKDIR` for custom server builds. The effective working directory is whatever your base image defines (often `/`).

If your server expects a specific working directory, set it in your `start_command`:

```yaml config.yaml theme={"system"}
docker_server:
  start_command: sh -c "cd /app && ./my-server"
```

### Secrets

Secrets declared in `config.yaml` are mounted as read-only files at `/secrets/{secret_name}`. See [Secrets in custom Docker images](/development/model/secrets#use-secrets-in-custom-docker-images) for usage.

## Runtime environment

Baseten sets specific environment variables in every custom-server container to route traffic to your server, identify the container in logs and traces, and keep its runtime path intact. These names are reserved. If you set any of them in `environment_variables`, Baseten drops the value before deploying the container:

* `PORT`, `HOST`, `HOSTNAME`
* `*_SERVICE_HOST`, `*_SERVICE_PORT*`
* `KUBERNETES_*`
* `K_SERVICE`, `K_REVISION`, `K_CONFIGURATION`
* `PATH`

Truss warns when it loads your config if you set `PORT` or `HOSTNAME`.

<Warning>
  `PORT` is set to `8080` inside every container. Baseten's reverse proxy listens on that port, so every container inherits `PORT=8080` regardless of what your server binds to.

  If your server code reads `os.environ.get("PORT", 8000)` (or similar), it gets `8080` instead of your default. Bind your server directly to `docker_server.server_port`, or read the port from an environment variable you control (for example, `MY_SERVER_PORT`).
</Warning>

### Platform-injected environment variables

Baseten sets these in every container at runtime:

| Variable                 | Value                                       |
| ------------------------ | ------------------------------------------- |
| `APP_HOME`               | `/app`                                      |
| `HOME`                   | `/home/app` (or `/root` if running as root) |
| `PYTHON_EXECUTABLE`      | Path to `python3` in the base image         |
| `BT_MODEL_ID`            | The model's ID                              |
| `BT_MODEL_DEPLOYMENT_ID` | The deployment's ID                         |

Read `BT_MODEL_ID` and `BT_MODEL_DEPLOYMENT_ID` from your server process to tag logs, metrics, or cache keys with deployment identity.

### Environment name

The [`environment` keyword argument](/deployment/environments#environment-access-in-code) is only available to Python Truss models. A custom server reads its environment from the filesystem instead. For deployments associated with an environment, `/etc/b10_dynamic_config/environment` contains a JSON object with the environment name:

```json /etc/b10_dynamic_config/environment theme={"system"}
{ "name": "production" }
```

Read it at runtime, handling the case where the file is absent or empty (a deployment not associated with an environment):

```python theme={"system"}
import json
from pathlib import Path


def get_environment_name():
    p = Path("/etc/b10_dynamic_config/environment")
    if p.exists():
        contents = p.read_text()
        if contents:
            return json.loads(contents).get("name")
    return None
```

Use the environment name to configure per-environment behavior, such as enabling monitoring or selecting which weights to load:

```python theme={"system"}
environment = get_environment_name()

if environment == "production":
    setup_sentry()
    model = load_production_weights()
else:
    model = load_default_weights()
```

### Base image environment variables

Environment variables baked into your base image (`ENV UV_EXTRA_INDEX_URL=...`, `ENV PIP_CONSTRAINT=...`, and so on) are visible to your server process at runtime. If your `start_command` or anything it invokes runs `uv` or `pip`, these inherited settings take effect. They don't affect how Truss builds the container's internal Python environment that runs the reverse proxy and process supervisor.

If you want a clean install environment inside `start_command`, unset the inherited variables before invoking `uv` or `pip`.

## Base image requirements

Standard (non-`no_build`) custom-server builds require:

* A **Debian-based** base image (`ID=debian` or `ID_LIKE=debian` in `/etc/os-release`).
* **Python 3.x** on `PATH`. The minor version is validated at build time.

[No-build](#no-build-deployment) mode has no base image restrictions: your image is used as-is.

## Per-request logging

Baseten assigns a unique request ID to every predict call and returns it in the `X-Baseten-Request-Id` response header. You can use this ID to [filter your model's logs](/observability/logs) down to a single request.

For standard Truss models, request ID logging is automatic. For custom HTTP servers, you'll need to extract the request ID from the incoming request header and include it in your JSON log output.

Extract the request ID from the `X-Baseten-Request-Id` header:

<Tabs>
  <Tab title="FastAPI">
    ```python server.py theme={"system"}
    import json
    import logging
    import sys

    from fastapi import FastAPI, Request


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

    app = FastAPI()


    @app.post("/predict")
    async def predict(request: Request):
        request_id = request.headers.get("x-baseten-request-id")

        logger.info("Predict called", extra={"request_id": request_id})

        # ... your inference logic ...

        logger.info("Predict complete", extra={"request_id": request_id})
        return {"result": "..."}
    ```
  </Tab>

  <Tab title="Flask">
    ```python server.py theme={"system"}
    import json
    import logging
    import sys

    from flask import Flask, request


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

    app = Flask(__name__)


    @app.route("/predict", methods=["POST"])
    def predict():
        request_id = request.headers.get("x-baseten-request-id")

        logger.info("Predict called", extra={"request_id": request_id})

        # ... your inference logic ...

        logger.info("Predict complete", extra={"request_id": request_id})
        return {"result": "..."}
    ```
  </Tab>
</Tabs>

<Note>
  Logs must be JSON formatted and written to stdout. The `request_id` field must be a top-level key in the JSON object.
</Note>

## No-build deployment

For security-hardened images that must remain completely unmodified, use [`no_build`](/reference/truss-configuration#no_build) to skip the build step entirely. Baseten copies the image to its container registry without running `docker build`.

No-build is only available for custom server deployments. Your Truss must use `docker_server` configuration. Standard Truss models with a `model.py` don't support `no_build`.

Point `base_image` at your hardened image and configure `docker_server` in `config.yaml`:

```yaml config.yaml theme={"system"}
base_image:
  image: your-registry/your-hardened-image:latest
docker_server:
  no_build: true
  server_port: 8000
  predict_endpoint: /predict
  readiness_endpoint: /health
  liveness_endpoint: /health
```

Set `no_build: true` and configure your server's port and endpoints. Since the image runs unmodified, it must include its own HTTP server and health check endpoints.

`start_command` is optional with `no_build`. If omitted, the image's original `ENTRYPOINT` runs. If your image needs a different startup command, set `start_command` to override the entrypoint.

### Runtime contract differences

No-build containers bypass Baseten's reverse proxy and process supervisor, which changes a few things relative to a standard build:

* **Port `8080` is not reserved.** Your server can bind to any port, including `8080`.
* **Your server is directly exposed** on `docker_server.server_port`.
* **Path routing is 1:1.** See [Routing](#routing) below.
* **The `data/` directory is still copied** to `/app/data` if present in your Truss.

### Routing

No-build deployments skip the URL remapping that standard custom server deployments use. All paths exposed by your server are accessible directly through Baseten's routing. For example, if your server exposes `/v2/listen/stream`, you can reach it at:

```txt theme={"system"}
https://model-<model_id>.api.baseten.co/environments/production/sync/v2/listen/stream
```

<Warning>
  `predict_endpoint` has no effect on no-build deployments because Baseten does not remap paths. However, it's still a required field, so setting it correctly serves as useful documentation of your server's primary inference route.
</Warning>

### Constraints

* Requires a custom server deployment with `docker_server` configuration. Standard Truss models with a `model.py` don't support `no_build`.
* Development mode is not supported. Deploy with `truss push` (published deployments are the default).
* Truss config fields beyond `docker_server`, `base_image`, `environment_variables`, `secrets`, and `data` are not available. Pass any additional configuration as environment variables.
* If your image runs as a specific user, set `run_as_user_id` to that UID.

### Pass configuration as environment variables

Since Truss config fields aren't injected into no-build containers, use `environment_variables` to pass configuration:

```yaml config.yaml theme={"system"}
base_image:
  image: your-registry/your-hardened-image:latest
docker_server:
  no_build: true
  server_port: 8000
  predict_endpoint: /predict
  readiness_endpoint: /health
  liveness_endpoint: /health
environment_variables:
  MODEL_NAME: my-model
  MAX_BATCH_SIZE: "32"
```

Access these in your server code with `os.environ["MODEL_NAME"]`.

## Next steps

* [Private registries](/development/model/dependencies#private-registries): Pull images from AWS ECR, Google Artifact Registry, or Docker Hub
* [Secrets](/development/model/secrets#custom-docker-images): Access API keys and tokens in your container
* [WebSockets](/development/model/websockets#websocket-usage-with-custom-servers): Enable WebSocket connections
* [vLLM](/examples/vllm), [SGLang](/examples/sglang), [TensorRT-LLM](/examples/tensorrt-llm): Deploy LLMs with popular inference servers
