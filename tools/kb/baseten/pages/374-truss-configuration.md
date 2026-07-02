# Truss configuration
Source: https://docs.baseten.co/reference/truss-configuration

Set your model resources, dependencies, and more

The `config.yaml` file defines how your model runs on Baseten: its dependencies,
compute resources, secrets, and runtime behavior. You specify what your model
needs; Baseten handles the infrastructure.

Every Truss includes a `config.yaml` in its root directory. Every value has a
default, so you only set what you need to change.

Common configuration tasks include:

* [Allocate GPU and memory](#resources): compute resources for your instance.
* [Declare environment variables](#param-environment-variables): environment variables for your model.
* [Configure concurrency](#runtime): parallel request handling.
* [Use a custom Docker image](#base_image): deploy pre-built inference servers.

<Accordion title="YAML syntax">
  If you're new to YAML, here's a quick primer.
  The default config uses `[]` for empty lists and `{}` for empty dictionaries.
  When adding values, the syntax changes to indented lines:

  ```yaml theme={"system"}
  # Empty
  requirements: []
  secrets: {}

  # With values
  requirements:
    - torch
    - transformers
  secrets:
    hf_access_token: null
  ```
</Accordion>

## IDE support

Truss ships a JSON schema for `config.yaml`. Projects created with `truss init` include a schema reference automatically, giving you autocompletion, hover docs, and validation in any editor that supports the [YAML language server](https://github.com/redhat-developer/yaml-language-server) (VS Code, JetBrains, Neovim, and others).

To add schema support to an existing `config.yaml`, add this comment as the first line:

```yaml theme={"system"}
# yaml-language-server: $schema=https://raw.githubusercontent.com/basetenlabs/truss/main/truss/config.schema.json
```

## Example

The following example shows a config file for a GPU-accelerated text generation model:

```yaml config.yaml theme={"system"}
model_name: my-llm
description: A text generation model.
requirements:
  - torch
  - transformers
  - accelerate
resources:
  cpu: "4"
  memory: 16Gi
  accelerator: L4
secrets:
  hf_access_token: null
```

For more examples, see the
[truss-examples](https://github.com/basetenlabs/truss-examples) repository.

## Reference

<ParamField type="string">
  The name of your model.
  This is displayed in the model details page in the Baseten UI.
</ParamField>

<ParamField type="string">
  A description of your model.
</ParamField>

<ParamField type="string">
  The name of the class that defines your Truss model.
  This class must implement at least a `predict` method.
</ParamField>

<ParamField type="string">
  The folder containing your model class.
</ParamField>

<ParamField type="string">
  The folder for data files in your Truss. Access it in your model:

  ```python model/model.py theme={"system"}
  class Model:
    def __init__(self, **kwargs):
      data_dir = kwargs["data_dir"]

    # ...
  ```
</ParamField>

<ParamField type="string">
  The folder for custom packages in your Truss.

  Place your own code here to reference in `model.py`. For example, with this project structure:

  ```output theme={"system"}
  stable-diffusion/
      packages/
          package_1/
              subpackage/
                  script.py
      model/
          model.py
          __init__.py
      config.yaml
  ```

  Inside the `model.py` the package can be imported like this:

  ```python model/model.py theme={"system"}
  from package_1.subpackage.script import run_script

  class Model:
      def __init__(self, **kwargs):
          pass

      def load(self):
          run_script()

      ...
  ```
</ParamField>

<ParamField type="string[]">
  Use `external_package_dirs` to access custom packages located outside your Truss.
  This lets multiple Trusses share the same package.

  The following example shows a project structure where `shared_utils/` is outside the Truss:

  ```output theme={"system"}
  my-model/
      model/
          model.py
      config.yaml
  shared_utils/
      helpers.py
  ```

  Specify the path in your `config.yaml`:

  ```yaml config.yaml theme={"system"}
  external_package_dirs:
    - ../shared_utils/
  ```

  Then import the package in your `model.py`:

  ```python model.py theme={"system"}
  from shared_utils.helpers import process_input

  class Model:
      def predict(self, model_input):
          return process_input(model_input)
  ```
</ParamField>

<ParamField type="object">
  Key-value pairs exposed to the environment that the model executes in.
  Many Python libraries can be customized with environment variables.

  <Warning>
    Do not store secret values directly in environment variables (or anywhere in
    the config file). See the `secrets` field for information on properly managing
    secrets.
  </Warning>

  ```yaml theme={"system"}
  environment_variables:
    ENVIRONMENT: Staging
    DB_URL: https://my_database.example.com/
  ```

  Baseten reserves some variable names (for example, `PORT`, `HOSTNAME`, `PATH`) and drops them from this field at deploy time. For the full list and for variables Baseten injects at runtime, see [Runtime environment](/development/model/custom-server#runtime-environment).
</ParamField>

<ParamField type="object">
  A flexible field for additional metadata.
  The entire config file is available to your model at runtime.

  **Reserved keys** that Baseten interprets:

  * `example_model_input`: Sample input that populates the Baseten playground.

  For example, to configure a model with playground input and custom vLLM settings, use the following:

  ```yaml theme={"system"}
  model_metadata:
    example_model_input: {"prompt": "What is the meaning of life?"}
    vllm_config:
      tensor_parallel_size: 1
      max_model_len: 4096
  ```
</ParamField>

<ParamField type="string">
  Path to a dependency file. Supports `requirements.txt`, `pyproject.toml`, and `uv.lock`.
  Truss detects the format by filename. Pin versions for reproducibility.

  When set to a `pyproject.toml`, Truss installs packages from `[project.dependencies]`.
  When set to a `uv.lock`, a sibling `pyproject.toml` must exist in the same directory.

  ```yaml theme={"system"}
  requirements_file: ./requirements.txt
  ```

  ```yaml theme={"system"}
  requirements_file: ./pyproject.toml
  ```

  ```yaml theme={"system"}
  requirements_file: ./uv.lock
  ```
</ParamField>

<ParamField type="string[]">
  A list of Python dependencies in [pip requirements file format](https://pip.pypa.io/en/stable/reference/requirements-file-format/).
  Mutually exclusive with `requirements_file`. Only one can be specified.

  For example, to install pinned versions of the dependencies, use the following:

  ```yaml theme={"system"}
  requirements:
    - scikit-learn==1.0.2
    - threadpoolctl==3.0.0
    - joblib==1.1.0
    - numpy==1.20.3
    - scipy==1.7.3
  ```
</ParamField>

<ParamField type="string[]">
  System packages that you would typically install using `apt` on a Debian operating system.

  ```yaml theme={"system"}
  system_packages:
    - ffmpeg
    - libsm6
    - libxext6
  ```
</ParamField>

<ParamField type="string">
  The Python version to use.
  Supported versions:

  * `py39`
  * `py310`
  * `py311`
  * `py312`
  * `py313`
</ParamField>

<ParamField type="object">
  Declare secrets your model needs at runtime, such as API keys or access tokens.
  Store the actual values in your [organization settings](https://app.baseten.co/settings/secrets).

  <Warning>
    Never store actual secret values in config. Use `null` as a placeholder. The key name must match the secret name in your organization.
  </Warning>

  ```yaml theme={"system"}
  secrets:
    hf_access_token: null
  ```

  For more information, see [Secrets](/development/model/secrets).
</ParamField>

<ParamField type="string">
  The path to a file containing example inputs for your model.
</ParamField>

<ParamField type="boolean">
  If true, changes to your model code are automatically reloaded without restarting the server. Useful for development.
</ParamField>

<ParamField type="boolean">
  Whether to apply library patches for improved compatibility.
</ParamField>

## resources

The `resources` section specifies the compute resources that your model needs, including CPU, memory, and GPU resources.

You can configure resources in two ways:

**Option 1: Specify individual resource fields**

```yaml theme={"system"}
resources:
  accelerator: A10G
  cpu: "4"
  memory: 20Gi
```

Baseten provisions the smallest instance that meets the specified constraints.

**Option 2: Specify an exact instance type**

```yaml theme={"system"}
resources:
  instance_type: "A10Gx4x16"
```

Using `instance_type` lets you select an exact SKU from the [instance type reference](/deployment/resources#instance-type-reference). When `instance_type` is specified, other resource fields are ignored.

<ParamField type="string">
  CPU resources needed, expressed as either a raw number or "millicpus".
  For example, `1000m` and `1` are equivalent.
  Fractional CPU amounts can be requested using millicpus.
  For example, `500m` is half of a CPU core.
</ParamField>

<ParamField type="string">
  CPU RAM needed, expressed as a number with units.
  Units include "Gi" (Gibibytes), "G" (Gigabytes), "Mi" (Mebibytes), and "M" (Megabytes).
  For example, `1Gi` and `1024Mi` are equivalent.

  <Info>
    `Gi` in `resources.memory` refers to **Gibibytes**, which are slightly larger
    than **Gigabytes**.
  </Info>
</ParamField>

<ParamField type="string">
  The GPU type for your instance.
  Available GPUs:

  * `T4`
  * `L4`
  * `L40S`
  * `RTX_PRO_6000`
  * `A10G`
  * `V100`
  * `A100`
  * `A100_40GB`
  * `H100`
  * `H100_40GB` ([fractional GPU details](https://www.baseten.co/blog/using-fractional-h100-gpus-for-efficient-model-serving/))
  * `H200`
  * `B200`
  * `B300`

  To request multiple GPUs (for example, if the weights don't fit in a single GPU), use the `:` operator:

  ```yaml theme={"system"}
  resources:
    accelerator: L4:4 # Requests 4 L4s
  ```

  For more information, see how to [Manage resources](/deployment/resources).
</ParamField>

<ParamField type="string">
  The full SKU name for the instance type. When specified, `cpu`, `memory`, and `accelerator` fields are ignored.

  Use this field to select an exact instance type from the [instance type reference](/deployment/resources#instance-type-reference). The format is `<GPU_TYPE>:<vCPU>x<MEMORY>` for GPU instances, or the bare `<vCPU>x<MEMORY>` SKU for CPU-only instances.

  ```yaml theme={"system"}
  resources:
    instance_type: "L4:4x16"
  ```

  Examples:

  * `L4:4x16`: L4 GPU with 4 vCPUs and 16 GiB RAM.
  * `H100:8x80`: H100 GPU with 8 vCPUs and 80 GiB RAM (the exact specs vary by GPU type).
  * `4x16`: CPU-only instance with 4 vCPUs and 16 GiB RAM.
</ParamField>

<ParamField type="number">
  The number of nodes for multi-node deployments. Each node gets the specified resources.
</ParamField>

## runtime

Runtime settings for your model instance.

For example, to configure a high-throughput inference server with concurrency and health checks, use the following:

```yaml theme={"system"}
runtime:
  predict_concurrency: 256
  streaming_read_timeout: 120
  health_checks:
    restart_threshold_seconds: 600
    stop_traffic_threshold_seconds: 300
```

<ParamField type="number">
  The number of concurrent requests that can run in your model's predict method. Defaults to 1, meaning `predict` runs one request at a time. Increase this if your model supports parallelism.

  See [Autoscaling](/deployment/autoscaling/overview#scaling-triggers) for more detail.
</ParamField>

<ParamField type="number">
  The timeout in seconds for streaming read operations.
</ParamField>

<ParamField type="boolean">
  If true, enables trace data export with built-in OTEL instrumentation. By default, data is collected internally by Baseten for troubleshooting. You can also export to your own systems. See the [tracing guide](/observability/tracing). May add performance overhead.
</ParamField>

<ParamField type="boolean">
  If true, sets the Truss server log level to `DEBUG` instead of `INFO`.
</ParamField>

<ParamField type="object">
  The transport protocol for your model. Supports `http` (default), `websocket`, and `grpc`.

  ```yaml theme={"system"}
  runtime:
    transport:
      kind: websocket
      ping_interval_seconds: 30
      ping_timeout_seconds: 10
  ```
</ParamField>

<ParamField type="object">
  Custom health check configuration for your deployments. For details, see [health check configuration](/development/model/health-checks#health-check-configuration).

  ```yaml theme={"system"}
  runtime:
    health_checks:
      startup_threshold_seconds: 2400
      restart_threshold_seconds: 600
      stop_traffic_threshold_seconds: 300
  ```
</ParamField>

<ParamField type="number">
  How long the startup phase runs before marking the replica as unhealthy. During startup, readiness and liveness probes don't run. Values must be between `10` and `3000` seconds. Defaults to 30 minutes (`1800` seconds). See [health checks](/development/model/health-checks) for details.
</ParamField>

<ParamField type="number">
  How long health checks must continuously fail before Baseten stops traffic to the replica. Defaults to 30 minutes (`1800` seconds).
</ParamField>

<ParamField type="number">
  How long health checks must continuously fail before Baseten restarts the replica. Defaults to 30 minutes (`1800` seconds).
</ParamField>

<ParamField type="number">
  How long to wait before running health checks. Deprecated. Use `startup_threshold_seconds` instead.
</ParamField>

<ParamField type="object">
  SSH access configuration for model replicas. When `enabled` is `true`, Baseten installs an OpenSSH server in the model container so you can connect from a terminal after running [`truss ssh setup`](/reference/cli/truss/ssh#setup) once:

  ```sh theme={"system"}
  ssh model-<model_id>-<deployment_id>.ssh.baseten.co
  ```

  Enable it in your config:

  ```yaml theme={"system"}
  runtime:
    remote_ssh:
      enabled: true
  ```

  Inference SSH must be enabled for your organization. [Contact support](mailto:support@baseten.co) to request access.

  Not compatible with [`docker_server.run_as_user_id`](#param-run-as-user-id). SSH requires the default `app` user (UID `60000`).
</ParamField>

## base\_image

Use `base_image` to deploy a custom Docker image. This is useful for running scripts at build time or installing complex dependencies.

For more information, see [Deploy custom Docker images](/development/model/custom-server).

For example, to use the vLLM Docker image as your base, use the following:

```yaml theme={"system"}
base_image:
  image: vllm/vllm-openai:v0.7.3
  python_executable_path: /usr/bin/python
# ...
```

<ParamField type="string">
  The path to the Docker image, for example:

  * `vllm/vllm-openai`
  * `lmsysorg/sglang`
  * `nvcr.io/nvidia/nemo:23.03`

  <Note>
    When using image tags like `:latest`, Baseten uses a cached copy and may not reflect updates to the image. To pull a specific version, use image digests like `your-image@sha256:abc123...`.
  </Note>
</ParamField>

<ParamField type="string">
  A path to the Python executable on the image, for example `/usr/bin/python`.

  ```yaml theme={"system"}
  base_image:
    image: vllm/vllm-openai:v0.12.0
    python_executable_path: /usr/bin/python
  ```
</ParamField>

<ParamField type="object">
  Authentication configuration for a private Docker registry.

  ```yaml theme={"system"}
  base_image:
    docker_auth:
      auth_method: GCP_SERVICE_ACCOUNT_JSON
      secret_name: gcp-service-account
      registry: us-west2-docker.pkg.dev
  ```

  For more information, see [Private Docker registries](/development/model/dependencies#private-registries).
</ParamField>

<ParamField type="string">
  The authentication method for the private registry. Supported values:

  * `GCP_SERVICE_ACCOUNT_JSON` - authenticate with a [GCP service account](https://cloud.google.com/iam/docs/service-account-overview). Add your service account JSON blob as a Truss secret.
  * `AWS_IAM` - authenticate with an [AWS IAM service account](https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html). Add `aws_access_key_id` and `aws_secret_access_key` to your Baseten secrets.
  * `AWS_OIDC` - authenticate using AWS OIDC federation. Requires `aws_oidc_role_arn` and `aws_oidc_region`.
  * `GCP_OIDC` - authenticate using GCP Workload Identity Federation. Requires `gcp_oidc_service_account` and `gcp_oidc_workload_id_provider`.

  For `GCP_SERVICE_ACCOUNT_JSON`:

  ```yaml theme={"system"}
  base_image:
    docker_auth:
      auth_method: GCP_SERVICE_ACCOUNT_JSON
      secret_name: gcp-service-account
      registry: us-east4-docker.pkg.dev
  ```

  For `AWS_IAM`:

  ```yaml theme={"system"}
  base_image:
    docker_auth:
      auth_method: AWS_IAM
      registry: <aws account id>.dkr.ecr.<region>.amazonaws.com
  secrets:
    aws_access_key_id: null
    aws_secret_access_key: null
  ```

  For `AWS_OIDC`:

  ```yaml theme={"system"}
  base_image:
    docker_auth:
      auth_method: AWS_OIDC
      registry: <aws account id>.dkr.ecr.<region>.amazonaws.com
      aws_oidc_role_arn: arn:aws:iam::123456789012:role/my-role
      aws_oidc_region: us-east-1
  ```

  For `GCP_OIDC`:

  ```yaml theme={"system"}
  base_image:
    docker_auth:
      auth_method: GCP_OIDC
      registry: us-east4-docker.pkg.dev
      gcp_oidc_service_account: my-sa@my-project.iam.gserviceaccount.com
      gcp_oidc_workload_id_provider: projects/123/locations/global/workloadIdentityPools/my-pool/providers/my-provider
  ```
</ParamField>

<ParamField type="string">
  The Truss secret that stores the credential for authentication. Required for `GCP_SERVICE_ACCOUNT_JSON`. Ensure this secret is added to the `secrets` section.
</ParamField>

<ParamField type="string">
  The registry to authenticate to, for example `us-east4-docker.pkg.dev`.
</ParamField>

<ParamField type="string">
  The secret name for the AWS access key ID. Only used with `AWS_IAM` auth method.
</ParamField>

<ParamField type="string">
  The secret name for the AWS secret access key. Only used with `AWS_IAM` auth method.
</ParamField>

## docker\_server

Use `docker_server` to deploy a custom Docker image that has its own HTTP server, without writing a `Model` class. This is useful for deploying inference servers like vLLM or SGLang that provide their own endpoints.

See [Deploy custom Docker images](/development/model/custom-server) for usage details.

For example, to deploy vLLM serving Qwen 2.5 3B, use the following:

```yaml theme={"system"}
base_image:
  image: vllm/vllm-openai:v0.7.3
docker_server:
  start_command: vllm serve Qwen/Qwen2.5-3B-Instruct --enable-prefix-caching
  readiness_endpoint: /health
  liveness_endpoint: /health
  predict_endpoint: /v1/completions
  server_port: 8000
# ...
```

<ParamField type="string">
  The command to start the server. Required when `no_build` is not set or is `false`. When `no_build` is `true`, `start_command` is optional; if omitted, the image's original `ENTRYPOINT` runs.
</ParamField>

<ParamField type="number">
  The port where the server runs. Port 8080 is reserved by Baseten's internal reverse proxy and cannot be used.
</ParamField>

<ParamField type="string">
  The endpoint for inference requests. This is mapped to Baseten's `/predict` route.

  <Note>
    Has no effect when `no_build` is `true`. No-build deployments do not remap URLs, so all server paths are accessible directly. See [No-build deployment](/development/model/custom-server#no-build-deployment) for details.
  </Note>
</ParamField>

<ParamField type="string">
  The endpoint for [readiness probes](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/#readiness-probe). Determines when the container can accept traffic.
</ParamField>

<ParamField type="string">
  The endpoint for [liveness probes](https://kubernetes.io/docs/concepts/configuration/liveness-readiness-startup-probes/#liveness-probe). Determines if the container needs to be restarted.
</ParamField>

<ParamField type="number">
  The Linux UID to run the server process as inside the container. Use this when your base image expects a specific non-root user (for example, NVIDIA NIM containers).

  The specified UID must already exist in the base image. Values `0` (root) and `60000` (platform default) are not allowed.

  Baseten automatically sets ownership of `/app`, `/workspace`, the packages directory, and `$HOME` to this UID. If your server writes to other directories, ensure they are writable by this UID in your base image or through `build_commands`.
</ParamField>

<ParamField type="boolean">
  Skip the build step and deploy the base image as-is. Baseten copies the image to its container registry without running `docker build` or modifying the image in any way. Only available for [custom server deployments](/development/model/custom-server) that use `docker_server`.

  When `no_build` is `true`:

  * `start_command` is optional. If omitted, the image's original `ENTRYPOINT` runs.
  * Environment variables and secrets are available.
  * Development mode is not supported. Deploy with `truss push` (published deployments are the default).

  Use this for security-hardened images (for example, Chainguard) that must remain unmodified. [Contact support](mailto:support@baseten.co) to enable no-build deployments for your organization.

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

  See [No-build deployment](/development/model/custom-server#no-build-deployment) for usage details.
</ParamField>

<Note>
  The `/app` directory is reserved by Baseten. `/app`, `/home/app`, `/tmp`, `/workspace`, and `/packages` are writable in the container. See [Container filesystem](/development/model/custom-server#container-filesystem) for the full runtime contract. If you need other directories to be writable, use `run_as_user_id` or `build_commands` to set permissions.
</Note>

## external\_data

Use `external_data` to download remote files into your image at build time. This reduces cold-start time by making data available without downloading it at runtime. Each entry specifies a URL to fetch and a path relative to the data directory where the file is stored.

```yaml theme={"system"}
external_data:
  - url: https://my-bucket.s3.amazonaws.com/my-data.tar.gz
    local_data_path: my-data.tar.gz
```

<ParamField type="string">
  The URL to download data from.
</ParamField>

<ParamField type="string">
  Path relative to the data directory where the downloaded file is stored. For example, `my-data.tar.gz` is stored at `/app/data/my-data.tar.gz`.
</ParamField>

<ParamField type="string">
  An optional name for the download entry.
</ParamField>

<ParamField type="string">
  The download backend to use.
</ParamField>

## build\_commands

<ParamField type="string[]">
  A list of shell commands to run during Docker build. These commands execute after system packages and Python requirements are installed. Use them for any setup that can't be handled by `requirements` or `system_packages` alone.

  For example, to clone a GitHub repository into the container, use the following:

  ```yaml theme={"system"}
  build_commands:
    - git clone https://github.com/comfyanonymous/ComfyUI.git
  ```

  You can also combine `build_commands` with `docker_server` to deploy third-party inference servers. The following example installs Ollama at build time and runs it as a Docker server:

  ```yaml theme={"system"}
  model_name: ollama-tinyllama
  base_image:
    image: python:3.11-slim
  build_commands:
    - curl -fsSL https://ollama.com/install.sh | sh
  docker_server:
    start_command: sh -c "ollama serve & sleep 5 && ollama pull tinyllama && wait"
    readiness_endpoint: /api/tags
    liveness_endpoint: /api/tags
    predict_endpoint: /api/generate
    server_port: 11434
  resources:
    cpu: "4"
    memory: 8Gi
  ```

  For more information, see [Build commands](/development/model/custom-server).
</ParamField>

## build

The `build` section handles secret access during Docker builds.
Other build-time configuration options are:

* [`build_commands`](#build_commands): shell commands to run during build.
* [`requirements`](#requirements): Python packages to install.
* [`system_packages`](#system_packages): apt packages to install.
* [`base_image`](#base_image): custom Docker base image.

<ParamField type="object">
  Grants access to secrets during the build.
  Provide a mapping between a secret and a path on the image.
  You can then access the secret in commands specified in `build_commands` by running `cat` on the file.

  For example, to install a pip package from a private GitHub repository, use the following:

  ```yaml theme={"system"}
  build_commands:
    - pip install git+https://$(cat /root/my-github-access-token)@github.com/path/to-private-repo.git
  build:
    secret_to_path_mapping:
      my-github-access-token: /root/my-github-access-token
  secrets:
    my-github-access-token: null
  ```

  Under the hood, this option mounts your secret as a build secret.
  The value of your secret will be secure and will not be exposed in your Docker history or logs.
</ParamField>

## weights <span>Preview</span>

Use `weights` to configure Baseten Delivery Network (BDN) for model weight delivery with multi-tier caching. This is the recommended approach for optimizing cold starts.

```yaml theme={"system"}
weights:
  - source: "hf://meta-llama/Llama-3.1-8B@main"
    mount_location: "/models/llama"
    allow_patterns: ["*.safetensors", "config.json"]
```

<Note>
  `weights` replaces the deprecated `model_cache` configuration. Use `truss migrate` to automatically convert your configuration.
</Note>

<ParamField type="string">
  URI specifying where to fetch weights from. Supported schemes:

  * `hf://`: Hugging Face Hub, for example `hf://meta-llama/Llama-3.1-8B@main`
  * `s3://`: AWS S3, for example `s3://my-bucket/models/weights`
  * `gs://`: Google Cloud Storage, for example `gs://my-bucket/models/weights`
  * `r2://`: Cloudflare R2, for example `r2://account_id.bucket/path`
</ParamField>

<ParamField type="string">
  Absolute path where weights will be mounted in your container. Must start with `/`.
</ParamField>

<ParamField type="string">
  Name of a Baseten secret containing credentials for private weight sources.
</ParamField>

<ParamField type="object">
  Authentication configuration for accessing private weight sources. Required for OIDC-based authentication. Supported `auth_method` values:

  * `CUSTOM_SECRET`: use a Baseten secret (specify `auth_secret_name`).
  * `AWS_OIDC`: use AWS OIDC federation (requires `aws_oidc_role_arn` and `aws_oidc_region`).
  * `GCP_OIDC`: use GCP Workload Identity Federation (requires `gcp_oidc_service_account` and `gcp_oidc_workload_id_provider`).

  For AWS OIDC:

  ```yaml theme={"system"}
  weights:
    - source: "s3://my-bucket/models/weights"
      mount_location: "/models/weights"
      auth:
        auth_method: AWS_OIDC
        aws_oidc_role_arn: arn:aws:iam::123456789012:role/my-role
        aws_oidc_region: us-east-1
  ```

  For GCP OIDC:

  ```yaml theme={"system"}
  weights:
    - source: "gs://my-bucket/models/weights"
      mount_location: "/models/weights"
      auth:
        auth_method: GCP_OIDC
        gcp_oidc_service_account: my-sa@my-project.iam.gserviceaccount.com
        gcp_oidc_workload_id_provider: projects/123/locations/global/workloadIdentityPools/my-pool/providers/my-provider
  ```
</ParamField>

<ParamField type="string[]">
  File patterns to include. Uses `fnmatch`-style wildcards. Patterns like `*.safetensors` only match at the root level; use `**/*.safetensors` for recursive matching across subdirectories.
</ParamField>

<ParamField type="string[]">
  File patterns to exclude. Uses `fnmatch`-style wildcards. Patterns like `*.bin` only match at the root level; use `**/*.bin` for recursive matching across subdirectories.
</ParamField>

For full documentation, see [Baseten Delivery Network (BDN)](/development/model/bdn).

## model\_cache <span>Deprecated</span>

<Warning>
  `model_cache` is deprecated. Use [`weights`](#weights) instead for faster cold starts through multi-tier caching.
</Warning>

Use `model_cache` to bundle model weights into your image at build time, reducing cold start latency.

For example, to cache Llama 2 7B weights from Hugging Face, use the following:

```yaml theme={"system"}
model_cache:
  - repo_id: NousResearch/Llama-2-7b-chat-hf
    revision: main
    ignore_patterns:
      - "*.bin"
    use_volume: true
    volume_folder: llama-2-7b-chat-hf
```

<Note>
  Despite the name `model_cache`, there are multiple backends supported, not just Hugging Face.
  You can also cache weights stored on GCS, S3, or Azure.
</Note>

<ParamField type="string">
  The source path for your model weights.
  For example, to cache weights from a Hugging Face repo, use the following:

  ```yaml theme={"system"}
  model_cache:
    - repo_id: madebyollin/sdxl-vae-fp16-fix
  ```

  Or you can cache weights from buckets like GCS or S3, using the following options:

  ```yaml theme={"system"}
  model_cache:
    - repo_id: gcs://path-to-my-bucket
      kind: gcs
    - repo_id: s3://path-to-my-bucket
      kind: s3
  ```
</ParamField>

<ParamField type="string">
  The source kind for the model cache.
  Supported values: `hf` (Hugging Face), `gcs`, `s3`, `azure`.
</ParamField>

<ParamField type="string">
  The revision of your Hugging Face repo.
  Required when `use_volume` is true for Hugging Face repos.
</ParamField>

<ParamField type="boolean">
  If true, caches model artifacts outside the container image. Recommended: `true`.
</ParamField>

<ParamField type="string">
  The location of the mounted folder. Required when `use_volume` is true.
  For example, `volume_folder: myrepo` makes the model available under `/app/model_cache/myrepo` at runtime.
</ParamField>

<ParamField type="string[]">
  File patterns to include in the cache. Uses Unix shell-style wildcards.
  By default, all paths are included.
</ParamField>

<ParamField type="string[]">
  File patterns to ignore, streamlining the caching process. Use Unix shell-style wildcards. Example: `["*.onnx", "Readme.md"]`. By default, nothing is ignored.
</ParamField>

<ParamField type="string">
  The secret name to use for runtime authentication, for example when accessing private Hugging Face repos.
</ParamField>

## trt\_llm

Configure TensorRT-LLM for optimized LLM inference on Baseten. TRT-LLM supports two inference stacks:

* **v1**: Best for dense models, small models, and embedding models. Supports lookahead speculative decoding and LoRA adapters.
* **v2**: Best for MoE models (Qwen3-MoE, DeepSeek, Kimi) and multi-node setups.

```yaml config.yaml theme={"system"}
trt_llm:
  inference_stack: v2
  build:
    checkpoint_repository:
      source: HF
      repo: meta-llama/Llama-3.1-8B-Instruct
    quantization_type: fp8
  runtime:
    max_batch_size: 256
    max_num_tokens: 8192
    tensor_parallel_size: 1
resources:
  accelerator: H100
```

<ParamField type="string">
  The inference stack version to use.

  Supported values:

  * `v1`: Use for dense models, small models, and embedding/reranking models. Supports lookahead speculative decoding and LoRA adapters.
  * `v2`: Use for MoE models and multi-node setups. The v2 runtime manages build parameters automatically; only `checkpoint_repository`, `quantization_type`, and `num_builder_gpus` can be set under `build`.
</ParamField>

### build

Build-time configuration for TRT-LLM engine compilation.

<ParamField type="string">
  The model architecture type.

  Supported values:

  * `decoder`: For generative causal LLMs (Llama, Qwen, Mistral, DeepSeek). Auto-detects architecture from the checkpoint.
  * `encoder`: For causal embedding models. Optimized for throughput with models like Qwen3-8B for embeddings.
  * `encoder_bert`: For BERT-based models (classification, reranking, embeddings). Optimized for throughput and cold-start latency of models under 4B parameters.
</ParamField>

<ParamField type="object">
  The model checkpoint to compile. See [checkpoint\_repository](#checkpoint_repository) for sub-fields.
</ParamField>

<ParamField type="string">
  The quantization method for the model weights. Use `no_quant` for fp16/bf16 (uses the precision from the model's `config.json`).

  Supported values:

  * `no_quant`: No quantization (fp16 or bf16).
  * `fp8`: FP8 weights with 16-bit KV cache.
  * `fp8_kv`: FP8 weights with FP8 KV cache. Faster attention with FP8 context FMHA. Not compatible with models that use `bias=True` (for example, Qwen 2.5).
  * `fp4`: FP4 weights with 16-bit KV cache. Requires B200 or newer GPUs.
  * `fp4_kv`: FP4 weights with FP8 KV cache. Requires B200 or newer GPUs.
  * `fp4_mlp_only`: FP4 quantization applied only to MLP layers, with 16-bit KV cache. Requires B200 or newer GPUs.
</ParamField>

<ParamField type="number">
  Number of GPUs for tensor parallelism. Must equal the number of GPUs in your `resources.accelerator` setting for v1.
</ParamField>

<ParamField type="number">
  Maximum sequence length the engine supports. Automatically inferred from the model checkpoint when not set. For encoder models, this is inferred from `max_position_embeddings` in the model's config.
</ParamField>

<ParamField type="number">
  Maximum number of requests batched together in one forward pass. Range: 1 to 2048.
</ParamField>

<ParamField type="number">
  Maximum number of tokens batched together in one forward pass. For encoder models and generative models without chunked prefill, this limits the max context length. Range: 65 to 1048576.
</ParamField>

<ParamField type="number">
  Number of GPUs to use during engine compilation. Set this higher than the deployment GPU count if quantization causes out-of-memory errors during the build step. If you run out of CPU memory, add more memory in the `resources` section instead.
</ParamField>

<ParamField type="object">
  A mapping of LoRA adapter names to checkpoint repositories. Each key becomes the `model` name in OpenAI-compatible API requests. Only supported on the v1 inference stack.

  ```yaml theme={"system"}
  trt_llm:
    build:
      lora_adapters:
        my-adapter:
          source: HF
          repo: my-org/my-lora-adapter
      lora_configuration:
        max_lora_rank: 64
  ```
</ParamField>

<ParamField type="object">
  LoRA configuration. See [lora\_configuration](#lora_configuration) for sub-fields. Only supported on the v1 inference stack.
</ParamField>

<ParamField type="object">
  Speculative decoding configuration. See [speculator](#speculator) for sub-fields. Only supported on the v1 inference stack.
</ParamField>

<ParamField type="number">
  Expert parallelism setting for MoE models. Set to `-1` to let the runtime decide. When set explicitly, must be a positive number less than or equal to `tensor_parallel_count`, and `tensor_parallel_count` should be divisible by this value for optimal performance.
</ParamField>

#### checkpoint\_repository

The model checkpoint to compile. Specifies the source, repository path, and optional credentials.

<ParamField type="string">
  Where to fetch the checkpoint from.

  Supported values:

  * `HF`: Hugging Face Hub.
  * `S3`: AWS S3 bucket (for example, `s3://my-bucket/path/to/checkpoint`).
  * `GCS`: Google Cloud Storage bucket (for example, `gcs://my-bucket/path/to/checkpoint`).
  * `AZURE`: Azure Blob Storage.
  * `REMOTE_URL`: HTTP URL to a tar.gzip archive (for example, a presigned URL).
  * `BASETEN_TRAINING`: Deploy from a Baseten training job. Use the training job ID as `repo` and the run revision as `revision`.
</ParamField>

<ParamField type="string">
  The repository path. For `HF`, this is the Hugging Face repo ID (for example, `meta-llama/Llama-3.1-8B-Instruct`). For `S3`/`GCS`/`AZURE`, this is the bucket path. The checkpoint must contain `config.json` and model files in safetensors format.
</ParamField>

<ParamField type="string">
  The revision or version of the checkpoint. For `HF` sources, this is the branch, tag, or commit hash. Required for `BASETEN_TRAINING` sources.
</ParamField>

<ParamField type="string">
  The name of the Baseten secret that stores the access credential. Must match a key in your organization's [secret settings](https://app.baseten.co/settings/secrets).
</ParamField>

#### quantization\_config

Calibration settings for quantized models. Only relevant when `quantization_type` is not `no_quant`.

<ParamField type="number">
  Size of the calibration dataset. Must be a multiple of 64, between 64 and 16384. Increase for production runs (for example, 1536) or decrease for quick testing (for example, 256).
</ParamField>

<ParamField type="string">
  Hugging Face dataset to use for calibration. Uses the `train` split and quantizes based on the `text` column.
</ParamField>

<ParamField type="number">
  Maximum sequence length for calibration samples. Must be a multiple of 64, between 64 and 16384.
</ParamField>

### runtime (v1)

Runtime configuration for the v1 inference stack.

```yaml theme={"system"}
trt_llm:
  inference_stack: v1
  runtime:
    kv_cache_free_gpu_mem_fraction: 0.9
    enable_chunked_context: true
    batch_scheduler_policy: guaranteed_no_evict
    total_token_limit: 500000
  # ...
```

<ParamField type="number">
  Fraction of free GPU memory to allocate for the KV cache. Higher values allow more context but leave less room for other operations.
</ParamField>

<ParamField type="number">
  Bytes of host (CPU) memory to reserve for KV cache offloading. Set to a high value to enable KV cache offload to host memory when GPU memory is constrained.
</ParamField>

<ParamField type="boolean">
  Whether to process long contexts in chunks. Requires `paged_kv_cache` and `use_paged_context_fmha` to be enabled in the build plugin configuration.
</ParamField>

<ParamField type="string">
  The batch scheduling strategy.

  Supported values:

  * `guaranteed_no_evict`: Guarantees scheduling with the requested number of tokens. May queue requests if memory is insufficient. Recommended for most use cases.
  * `max_utilization`: Schedules requests without checking available memory. May need to pause requests if memory fills up.
</ParamField>

<ParamField type="number">
  Default maximum number of tokens per request when not specified by the client.
</ParamField>

<ParamField type="string">
  The model name returned in OpenAI-compatible API responses. Only for generative (decoder) models.
</ParamField>

<ParamField type="number">
  Maximum number of tokens scheduled at once to the C++ engine. Only for generative (decoder) models.
</ParamField>

<ParamField type="string">
  Default API route for the model. Auto-detected from the model architecture for encoder models.

  Supported values:

  * `/v1/embeddings`: For embedding models.
  * `/rerank`: For reranking models.
  * `/predict`: For sequence classification models.
</ParamField>

### runtime (v2)

Runtime configuration for the v2 inference stack.

```yaml theme={"system"}
trt_llm:
  inference_stack: v2
  runtime:
    max_batch_size: 256
    max_num_tokens: 8192
    tensor_parallel_size: 1
  # ...
```

<ParamField type="number">
  Maximum sequence length. Range: 1 to 1048576.
</ParamField>

<ParamField type="number">
  Maximum number of requests batched together in one forward pass. Range: 1 to 2048.
</ParamField>

<ParamField type="number">
  Maximum number of tokens batched together in one forward pass. Range: 65 to 131072.
</ParamField>

<ParamField type="number">
  Number of GPUs for tensor parallelism.
</ParamField>

<ParamField type="boolean">
  Whether to enable chunked prefill for generative (decoder) models.
</ParamField>

<ParamField type="string">
  The model name returned in OpenAI-compatible API responses. Only for generative (decoder) models.
</ParamField>

### speculator

Configure speculative decoding to speed up inference by predicting multiple tokens per step. Only supported on the v1 inference stack.

```yaml theme={"system"}
trt_llm:
  build:
    speculator:
      speculative_decoding_mode: LOOKAHEAD_DECODING
      lookahead_windows_size: 7
      lookahead_ngram_size: 5
      lookahead_verification_set_size: 3
    max_batch_size: 64
    # ...
```

<Note>
  Speculative decoding works best at lower batch sizes (under 64). For high-throughput use cases, tune concurrency settings for more aggressive autoscaling instead.
</Note>

<ParamField type="string">
  The speculative decoding strategy.

  Supported values:

  * `LOOKAHEAD_DECODING`: N-gram based speculation built into the runtime. Recommended for most use cases, especially code editing workloads where n-gram patterns are common.
</ParamField>

<ParamField type="number">
  Lookahead window size for the `LOOKAHEAD_DECODING` mode. Required when using lookahead decoding. Recommended values: 5 to 8.
</ParamField>

<ParamField type="number">
  N-gram size for the `LOOKAHEAD_DECODING` mode. Required when using lookahead decoding. Recommended values: 3 to 5.
</ParamField>

<ParamField type="number">
  Verification set size for the `LOOKAHEAD_DECODING` mode. Required when using lookahead decoding. Recommended values: 3 to 5.
</ParamField>

<ParamField type="number">
  Maximum number of speculative tokens per step. Auto-calculated from the lookahead parameters when using `LOOKAHEAD_DECODING`. Maximum: 2048.
</ParamField>

<ParamField type="boolean">
  Enable the Baseten-optimized lookahead algorithm. Requires `speculative_decoding_mode` to be `LOOKAHEAD_DECODING`. When enabled with `(window_size, 1, 1)` settings (for example, `(8, 1, 1)` or `(32, 1, 1)`), enables dynamic speculation.
</ParamField>

### lora\_configuration

LoRA adapter settings for the v1 inference stack. Use with `lora_adapters` to serve multiple fine-tuned models from a single deployment.

<ParamField type="number">
  Maximum LoRA rank across all adapters.
</ParamField>

<ParamField type="string[]">
  List of model modules to apply LoRA to.
</ParamField>

## bis\_llm <span>Preview</span>

Configuration for deploying [BIS-LLM](/engines/bis-llm/overview) models, Baseten's next-generation engine for Mixture of Experts and other large LLMs. This is a preview API and may change in future releases.

<Note>
  BIS-LLM deployments take a separate path from standard `trt_llm` deployments. Several `truss push` flags are not supported: development deployments (the deployment must be published), `--promote`, `--environment`, `--preserve-previous-production-deployment`, `--disable-truss-download`, `--deployment-name`, and `--deploy-timeout-minutes`.
</Note>

<BisLlmEnterpriseGate />

```yaml theme={"system"}
bis_llm:
  version: "1.0.0"
  config:
    # BIS-LLM stack configuration (key/value pairs accepted by the chosen version)
  additional_autoscaling_config:
    metrics:
      - name: in_flight_tokens
        target: 1000
```

<ParamField type="string">
  The version of the BIS-LLM deployment stack to use.
</ParamField>

<ParamField type="object">
  Stack configuration passed through to the BIS-LLM deployment. The accepted keys depend on the chosen `version`.
</ParamField>

<ParamField type="object">
  Additional autoscaling configuration for in-flight token metrics.
</ParamField>

<ParamField type="object[]">
  List of metric targets for autoscaling. Each entry has a `name` (string) and `target` (number).
</ParamField>

## training\_checkpoints

Configuration for deploying models from training checkpoints.

For example, to deploy a model using checkpoints from a training job, use the following:

```yaml theme={"system"}
training_checkpoints:
  download_folder: /tmp/training_checkpoints
  artifact_references:
    - training_job_id: tr_abc123
      paths:
        - "checkpoint-*"
```

<ParamField type="string">
  The folder to download the checkpoints to.
</ParamField>

<ParamField type="object[]">
  A list of artifact references to download.
</ParamField>

<ParamField type="string">
  The training job ID that the artifact reference belongs to.
</ParamField>

<ParamField type="string[]">
  The paths of the files to download, which can contain `*` or `?` wildcards.
</ParamField>

<Note>
  The following environment variables are reserved by the platform and will be overwritten at runtime: `PORT`, `HOSTNAME`. You'll see a warning if you attempt to set these in your config.
</Note>
