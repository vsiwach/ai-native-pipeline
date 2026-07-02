# Training SDK
Source: https://docs.baseten.co/reference/sdk/training

API reference for the Baseten training SDK.

## Installation

Truss includes the training SDK:

<Tabs>
  <Tab title="uv (recommended)">
    [uv](https://docs.astral.sh/uv/) is a fast Python package manager. Create a virtual environment and install Truss:

    ```sh theme={"system"}
    uv venv && source .venv/bin/activate
    uv pip install truss
    ```
  </Tab>

  <Tab title="pip (macOS/Linux)">
    Create a virtual environment and install Truss with pip:

    ```sh theme={"system"}
    python3 -m venv .venv && source .venv/bin/activate
    pip install --upgrade truss
    ```
  </Tab>

  <Tab title="pip (Windows)">
    Create a virtual environment and install Truss with pip:

    ```sh theme={"system"}
    python3 -m venv .venv && .venv\Scripts\activate
    pip install --upgrade truss
    ```
  </Tab>
</Tabs>

Define your training job in a configuration file (typically `config.py`). Import the SDK and accelerator config:

```python config.py theme={"system"}
from truss_train import definitions
from truss.base import truss_config
```

You can also import classes directly from `truss_train` (for example, `from truss_train import Compute, Runtime`).

***

## Complete example

Copy this `config.py` as a starting point for your training project. It configures [caching](/training/concepts/cache) to persist pip packages between jobs, [checkpointing](/training/concepts/checkpoints) to save model weights, and GPU compute on a single H200 node. Modify the `start_commands`, `environment_variables`, and `accelerator` fields for your use case. For more examples, see [ml-cookbook](https://github.com/basetenlabs/ml-cookbook/tree/main/examples).

```python config.py theme={"system"}
from truss_train import definitions
from truss.base import truss_config

# The Docker image your training code runs in.
BASE_IMAGE = "pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime"

# Runtime controls what happens when the container starts: which commands
# run, which secrets are injected, and whether caching and checkpointing
# are enabled.
training_runtime = definitions.Runtime(
    start_commands=[
        "pip install transformers datasets accelerate",
        "torchrun --nproc-per-node=2 train.py",
    ],
    environment_variables={
        "HF_TOKEN": definitions.SecretReference(name="hf_access_token"),
        "WANDB_API_KEY": definitions.SecretReference(name="wandb_api_key"),
    },
    # Cache persists pip packages and downloaded models between jobs.
    cache_config=definitions.CacheConfig(enabled=True),
    # Checkpointing writes model weights to $BT_CHECKPOINT_DIR for
    # deployment or resuming later.
    checkpointing_config=definitions.CheckpointingConfig(enabled=True),
)

# Compute defines the hardware allocated to each node.
training_compute = definitions.Compute(
    node_count=1,
    accelerator=truss_config.AcceleratorSpec(
        accelerator=truss_config.Accelerator.H200,
        count=2,
    ),
)

# TrainingJob combines the image, compute, and runtime into a single
# unit that Baseten provisions and runs.
training_job = definitions.TrainingJob(
    image=definitions.Image(base_image=BASE_IMAGE),
    compute=training_compute,
    runtime=training_runtime,
)

# TrainingProject groups related jobs under one name. Pushing this
# config creates the project (or reuses it) and submits a new job.
training_project = definitions.TrainingProject(
    name="llm-fine-tuning",
    job=training_job,
)
```

***

## push

Submits a training job to Baseten. Every config you define with the classes below does nothing until you call `push()`.

When you call `push()`, Baseten:

1. Authenticates with your Baseten account.
2. Creates the [training project](/training/overview) if one with the given name doesn't already exist, or reuses the existing project.
3. Archives your source directory (your training script, data files, and any other local files) and uploads it.
4. Submits a new training job. Baseten provisions the hardware, pulls the container image, mounts any [BDN weights](#weightssource), extracts your source files into the container, and runs your [start\_commands](#runtime).

The job then progresses through the [training lifecycle](/training/lifecycle):

* `CREATED`: Baseten has received the training configuration.
* `DEPLOYING`: Baseten is provisioning compute resources and installing dependencies.
* `RUNNING`: Your training code is actively executing.
* `COMPLETED`: The job has finished. Checkpoints and artifacts have been saved.
* `DEPLOY_FAILED`: The job failed to deploy, likely due to a bad image or resource allocation issue.
* `FAILED`: The job encountered an error. Check the logs for details.
* `STOPPED`: The job was manually stopped.

The CLI command `uvx truss train push config.py` performs the same steps with additional options for team selection and flag overrides.

The `push` function accepts either a file path or a `TrainingProject` object.

```python config.py theme={"system"}
from truss_train import push

# Pass a config file path:
def push(
    config: Path,
    *,
    remote: str = "baseten",
) -> dict

# Pass a TrainingProject object:
def push(
    config: TrainingProject,
    *,
    remote: str = "baseten",
    source_dir: Optional[Path] = None,
) -> dict
```

### Parameters

<ParamField type="Path | TrainingProject">
  Path to a `config.py` file or a [TrainingProject](#trainingproject) instance. When you pass a `Path`, Baseten imports the module and scans for an instance of `TrainingProject`. The module must contain exactly one.
</ParamField>

<ParamField type="string">
  Remote provider to push to. Defaults to `baseten`.
</ParamField>

<ParamField type="Path">
  Root directory whose contents Baseten uploads as the job's working directory. Baseten archives this directory and extracts it into the container before running [start\_commands](#runtime). Only applies when `config` is a `TrainingProject`. Defaults to the current directory.
</ParamField>

### Return value

Returns a dictionary containing the created training job. Use the `id` and `training_project.id` values to monitor the job, stream logs, and list checkpoints.

```json Output theme={"system"}
{
    "id": "gvpql31",
    "training_project_id": "aghi527",
    "training_project": {
        "id": "aghi527",
        "name": "llm-fine-tuning"
    },
    "current_status": "TRAINING_JOB_CREATED",
    "instance_type": { ... },
    "name": "fine-tune-v1",
    ...
}
```

For example, to submit a training job programmatically, pass a `TrainingProject` object to `push()`:

```python submit_job.py theme={"system"}
from pathlib import Path
from truss.base import truss_config
from truss_train import push, definitions

project = definitions.TrainingProject(
    name="llm-fine-tuning",
    job=definitions.TrainingJob(
        image=definitions.Image(base_image="pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime"),
        compute=definitions.Compute(
            accelerator=truss_config.AcceleratorSpec(
                accelerator=truss_config.Accelerator.H200,
                count=2,
            )
        ),
        runtime=definitions.Runtime(
            start_commands=["python train.py"],
            environment_variables={
                "HF_TOKEN": definitions.SecretReference(name="hf_access_token"),
            },
        ),
    ),
)

result = push(config=project, source_dir=Path("./training"))

print(f"Project ID: {result['training_project']['id']}")
print(f"Job ID: {result['id']}")
```

```text Output theme={"system"}
Project ID: aghi527
Job ID: gvpql31
```

### After submitting

Once `push()` returns, Baseten queues your job and begins provisioning. Use the returned job ID to track progress:

* **Stream logs:** `uvx truss train logs --job-id <job_id> --tail`
* **Check status:** `uvx truss train view --job-id <job_id>`
* **List checkpoints:** Use the [get training job checkpoints](/reference/training-api/get-training-job-checkpoints) API.
* **Deploy a checkpoint:** For more information, see [deploy checkpoints](#deploy-checkpoints).

For a complete working example, see the [programmatic training API recipe](https://github.com/basetenlabs/ml-cookbook/tree/main/recipes/programmatic-training-api). For `config.py`-based submission with the CLI, see the [training getting started guide](/training/getting-started).

***

## TrainingProject

Groups related training jobs under a single named project. When you [push](#push) a `TrainingProject`, Baseten creates the project if it doesn't exist, then submits the attached [TrainingJob](#trainingjob). All jobs in a project share the same [project-level cache](/training/concepts/cache) and appear together in the dashboard.

```python config.py theme={"system"}
from truss_train import definitions

project = definitions.TrainingProject(
    name="llm-fine-tuning",
    job=training_job,
    team_name="my-team",
)
```

### Parameters

<ParamField type="string">
  Project name. Reusing a name adds jobs to the existing project.
</ParamField>

<ParamField type="TrainingJob">
  Training job to submit. Defines the container image, compute resources, runtime commands, and optional weights. For more information, see [TrainingJob](#trainingjob).
</ParamField>

<ParamField type="string">
  Team that owns this project. Controls access and team-level cache scope.
</ParamField>

## TrainingJob

Represents a single training run. Baseten provisions the hardware specified in [Compute](#compute), pulls the container [Image](#image), uploads your source directory, mounts any [WeightsSource](#weightssource) volumes, then executes the [Runtime](#runtime) start commands. For more information, see the [training lifecycle](/training/lifecycle).

```python config.py theme={"system"}
from truss_train import definitions, WeightsSource
from truss.base import truss_config

training_job = definitions.TrainingJob(
    name="fine-tune-v1",
    image=definitions.Image(base_image="pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime"),
    compute=definitions.Compute(
        accelerator=truss_config.AcceleratorSpec(
            accelerator=truss_config.Accelerator.H200,
            count=4,
        )
    ),
    runtime=definitions.Runtime(
        start_commands=["chmod +x ./run.sh && ./run.sh"],
        checkpointing_config=definitions.CheckpointingConfig(enabled=True),
        cache_config=definitions.CacheConfig(enabled=True),
    ),
    weights=[
        WeightsSource(
            source="hf://meta-llama/Llama-3.1-8B@main",
            mount_location="/app/models/llama",
        ),
    ],
)
```

### Parameters

<ParamField type="Image">
  Docker image that provides the training environment, including the OS, CUDA drivers, and pre-installed libraries. For more information, see [Image](#image).
</ParamField>

<ParamField type="Compute">
  Hardware allocation for each node. Set the GPU type and count with `accelerator`, and increase `node_count` for distributed training. Defaults to `Compute()`. For more information, see [Compute](#compute).
</ParamField>

<ParamField type="Runtime">
  Controls container startup: shell commands to execute, environment variables to inject, and whether to enable caching or checkpointing. Defaults to `Runtime()`. For more information, see [Runtime](#runtime).
</ParamField>

<ParamField type="string">
  Display name for this job in the dashboard and API responses.
</ParamField>

<ParamField type="InteractiveSession">
  Opens a remote tunnel so you can attach VS Code or Cursor to the running container for live debugging. For more information, see [InteractiveSession](#interactivesession).
</ParamField>

<ParamField type="Workspace">
  Controls which local files Baseten uploads to the container. Use this to exclude large directories, include files from outside the root, or change the root entirely. For more information, see [Workspace](#workspace).
</ParamField>

<ParamField type="WeightsSource[]">
  Model weights that BDN mirrors and mounts read-only in the container. Supports Hugging Face, S3, GCS, Azure, R2, and direct URLs. For more information, see [WeightsSource](#weightssource).
</ParamField>

<ParamField type="bool">
  When `True` (default), Baseten uses `/b10/workspace` as the container's working directory, extracting your source files and base image working directory contents there. The `BT_WORKING_DIR` environment variable points to `/b10/workspace`. When `False`, the Docker image's default working directory is used and `BT_WORKING_DIR` is unset.
</ParamField>

## WeightsSource

Mounts pre-trained model weights into the training container as a read-only volume. Baseten mirrors the weights through [BDN](/development/model/bdn) before provisioning compute, so the data is on disk before your `start_commands` run.
On subsequent jobs, BDN serves the cached copy from a cluster- or node-local cache, which avoids re-downloading.
For the full delivery behavior, see [how BDN serves training jobs](/training/concepts/storage#how-bdn-serves-training-jobs).

<Tabs>
  <Tab title="Hugging Face">
    ```python config.py theme={"system"}
    from truss_train import WeightsSource

    WeightsSource(
        source="hf://Qwen/Qwen3-0.6B",
        mount_location="/app/models/Qwen/Qwen3-0.6B",
    )
    ```
  </Tab>

  <Tab title="S3 with auth">
    ```python config.py theme={"system"}
    from truss_train import WeightsSource

    WeightsSource(
        source="s3://my-bucket/training-data",
        mount_location="/app/data/training-data",
        auth={"auth_method": "CUSTOM_SECRET", "auth_secret_name": "aws_credentials"},
    )
    ```
  </Tab>

  <Tab title="File filtering">
    ```python config.py theme={"system"}
    from truss_train import WeightsSource

    WeightsSource(
        source="hf://meta-llama/Llama-3.1-8B@main",
        mount_location="/app/models/llama",
        allow_patterns=["*.safetensors", "config.json", "tokenizer.*"],
        ignore_patterns=["*.md", "*.txt"],
    )
    ```
  </Tab>
</Tabs>

### Parameters

<ParamField type="string">
  URI with scheme prefix.

  | Scheme  | Example                             | Description           |
  | ------- | ----------------------------------- | --------------------- |
  | `hf://` | `hf://meta-llama/Llama-3.1-8B@main` | Hugging Face Hub.     |
  | `s3://` | `s3://my-bucket/path/to/data`       | Amazon S3.            |
  | `gs://` | `gs://my-bucket/path/to/data`       | Google Cloud Storage. |
  | `r2://` | `r2://account_id.bucket/path`       | Cloudflare R2.        |

  For Hugging Face sources, pin to a specific revision with the `@revision` suffix (branch, tag, or commit SHA).
</ParamField>

<ParamField type="string">
  Absolute path where Baseten mounts the weights in the container.
</ParamField>

<ParamField type="WeightsAuth">
  Authentication configuration. See the [BDN configuration reference](/development/model/bdn#configuration-reference).
</ParamField>

<ParamField type="string">
  Baseten secret name for credentials.
</ParamField>

<ParamField type="string[]">
  File patterns to include during download.
</ParamField>

<ParamField type="string[]">
  File patterns to exclude during download.
</ParamField>

## Image

Sets the Docker image that Baseten pulls to create the training container. The image provides the OS, CUDA drivers, Python version, and any pre-installed libraries your training code needs. Use a public image from Docker Hub or a private image with [DockerAuth](#dockerauth).

```python config.py theme={"system"}
image = definitions.Image(
    base_image="pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime"
)
```

### Parameters

<ParamField type="string">
  Full Docker image tag, such as `"pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime"`.
</ParamField>

<ParamField type="DockerAuth">
  Credentials for pulling from private registries like AWS ECR or Google Container Registry. Store actual credentials as [Baseten secrets](/organization/secrets). For more information, see [DockerAuth](#dockerauth).
</ParamField>

### DockerAuth

Provides credentials for pulling images from private Docker registries (AWS ECR, Google Container Registry, etc.). Store the actual credential values as secrets in your [Baseten workspace](/organization/secrets) and reference them with [SecretReference](#secretreference).

<ParamField type="DockerAuthType">
  Authentication method.
</ParamField>

<ParamField type="string">
  Docker registry URL.
</ParamField>

<ParamField type="AWSIAMDockerAuth">
  IAM credentials for authenticating with AWS ECR. Requires `access_key_secret_ref` and `secret_access_key_secret_ref`. For more information, see [AWSIAMDockerAuth](#awsiamdockerauth).
</ParamField>

<ParamField type="GCPServiceAccountJSONDockerAuth">
  Service account JSON credentials for authenticating with Google Container Registry. For more information, see [GCPServiceAccountJSONDockerAuth](#gcpserviceaccountjsondockerauth).
</ParamField>

<ParamField type="RegistrySecretDockerAuth">
  Username/password credentials for authenticating with registries that support static credentials (Docker Hub, GHCR, NGC). Not compatible with AWS ECR or GCP Artifact Registry. For more information, see [RegistrySecretDockerAuth](#registrysecretdockerauth).
</ParamField>

#### AWSIAMDockerAuth

Authenticates with AWS ECR using IAM credentials.

```python config.py theme={"system"}
from truss.base import truss_config

image = definitions.Image(
    base_image="123456789.dkr.ecr.us-east-1.amazonaws.com/my-image:latest",
    docker_auth=definitions.DockerAuth(
        auth_method=truss_config.DockerAuthType.AWS_IAM,
        registry="123456789.dkr.ecr.us-east-1.amazonaws.com",
        aws_iam_docker_auth=definitions.AWSIAMDockerAuth(
            access_key_secret_ref=definitions.SecretReference(name="aws_access_key"),
            secret_access_key_secret_ref=definitions.SecretReference(name="aws_secret_access_key"),
        )
    )
)
```

<ParamField type="SecretReference">
  AWS access key ID, stored as a [Baseten secret](/organization/secrets) and referenced by name.
</ParamField>

<ParamField type="SecretReference">
  AWS secret access key, stored as a [Baseten secret](/organization/secrets) and referenced by name.
</ParamField>

#### GCPServiceAccountJSONDockerAuth

Authenticates with Google Container Registry using service account JSON.

```python config.py theme={"system"}
from truss.base import truss_config

image = definitions.Image(
    base_image="gcr.io/my-project/my-image:latest",
    docker_auth=definitions.DockerAuth(
        auth_method=truss_config.DockerAuthType.GCP_SERVICE_ACCOUNT_JSON,
        registry="gcr.io",
        gcp_service_account_json_docker_auth=definitions.GCPServiceAccountJSONDockerAuth(
            service_account_json_secret_ref=definitions.SecretReference(name="gcp_service_account_json"),
        )
    )
)
```

<ParamField type="SecretReference">
  GCP service account JSON, stored as a [Baseten secret](/organization/secrets) and referenced by name.
</ParamField>

#### RegistrySecretDockerAuth

Authenticates with registries that support static username/password credentials, including Docker Hub, GHCR, and NGC. For AWS ECR or GCP Artifact Registry, use [AWSIAMDockerAuth](#awsiamdockerauth) or [GCPServiceAccountJSONDockerAuth](#gcpserviceaccountjsondockerauth) instead.

```python config.py theme={"system"}
from truss.base import truss_config

image = definitions.Image(
    base_image="your-registry/your-image:latest",
    docker_auth=definitions.DockerAuth(
        auth_method=truss_config.DockerAuthType.REGISTRY_SECRET,
        registry="docker.io",
        registry_secret_docker_auth=definitions.RegistrySecretDockerAuth(
            secret_ref=definitions.SecretReference(name="my_docker_cred")
        )
    )
)
```

<ParamField type="SecretReference">
  Registry credentials in `username:password` format (plaintext, not Base64-encoded), stored as a [Baseten secret](/organization/secrets) and referenced by name.
</ParamField>

## Compute

Defines the hardware Baseten allocates for each training job. Set `node_count` above 1 for [multi-node distributed training](/training/concepts/multinode), which provisions multiple identical nodes and injects coordination environment variables (`BT_LEADER_ADDR`, `BT_NODE_RANK`, `BT_GROUP_SIZE`).

```python config.py theme={"system"}
from truss.base import truss_config

compute = definitions.Compute(
    node_count=2,
    cpu_count=8,
    memory="64Gi",
    accelerator=truss_config.AcceleratorSpec(
        accelerator=truss_config.Accelerator.H200,
        count=4,
    )
)
```

### Parameters

<ParamField type="integer">
  Number of nodes to provision. Each node gets the full CPU, memory, and GPU allocation.
</ParamField>

<ParamField type="integer">
  CPU cores per node.
</ParamField>

<ParamField type="string">
  RAM per node (for example, `"64Gi"`). Defaults to `2Gi`.
</ParamField>

<ParamField type="AcceleratorSpec">
  GPU type and count per node. For more information, see [AcceleratorSpec](#acceleratorspec).
</ParamField>

### AcceleratorSpec

Selects the GPU type and count per node. The `count` determines how many GPUs are available to your training script on each node (exposed as `$BT_NUM_GPUS`).

<ParamField type="Accelerator">
  GPU type.

  Available options:

  * `H100`: NVIDIA H100.
  * `H200`: NVIDIA H200.
</ParamField>

<ParamField type="integer">
  Number of GPUs per node.
</ParamField>

## Runtime

Controls what happens when the training container starts. Baseten executes `start_commands` in order inside the container. Use them to install dependencies, set up data, and launch your training script. Baseten injects environment variables before the first command runs; use [SecretReference](#secretreference) for sensitive values like API keys so they aren't stored in your config file.

```python config.py theme={"system"}
runtime = definitions.Runtime(
    start_commands=["chmod +x ./run.sh && ./run.sh"],
    environment_variables={
        "BATCH_SIZE": "32",
        "WANDB_API_KEY": definitions.SecretReference(name="wandb_api_key"),
        "HF_TOKEN": definitions.SecretReference(name="hf_access_token"),
    },
    checkpointing_config=definitions.CheckpointingConfig(enabled=True),
    cache_config=definitions.CacheConfig(enabled=True),
)
```

### Parameters

<ParamField type="string[]">
  Shell commands that Baseten executes sequentially when the container starts.
</ParamField>

<ParamField type="object">
  Key-value pairs that Baseten injects as env vars. Use [SecretReference](#secretreference) for sensitive values.
</ParamField>

<ParamField type="CheckpointingConfig">
  Enables writing model checkpoints to persistent storage. When enabled, Baseten mounts a volume and exports `$BT_CHECKPOINT_DIR`. Defaults to `CheckpointingConfig()`. For more information, see [CheckpointingConfig](#checkpointingconfig).
</ParamField>

<ParamField type="CacheConfig">
  Enables a persistent read-write cache that survives across jobs for pip packages, model downloads, and preprocessed datasets. For more information, see [CacheConfig](#cacheconfig).
</ParamField>

<ParamField type="LoadCheckpointConfig">
  Downloads checkpoints from a previous job into the container before `start_commands` run. Use this to resume training or initialize weights from an earlier experiment. For more information, see [LoadCheckpointConfig](#loadcheckpointconfig).
</ParamField>

<ParamField type="boolean">
  Use `cache_config` with `enabled=True` instead.
</ParamField>

### SecretReference

Injects a secret stored in your [Baseten workspace](/organization/secrets) as an environment variable at runtime. Baseten never writes the value to your config file or source code. Use this for API keys, tokens, and credentials.

```python config.py theme={"system"}
secret_ref = definitions.SecretReference(name="wandb_api_key")
```

<ParamField type="string">
  Name of the secret as it appears in your workspace settings.
</ParamField>

### CheckpointingConfig

Enables persistent checkpoint storage for the training job. When `enabled` is true, Baseten mounts a persistent volume and exports `$BT_CHECKPOINT_DIR` as an environment variable pointing to it. Your training script writes model weights, optimizer state, or any artifacts to that directory. These checkpoints survive job termination and can be [deployed to inference](/training/deployment) or [loaded into future jobs](#loadcheckpointconfig). See the [checkpointing guide](/training/concepts/checkpoints) for best practices.

```python config.py theme={"system"}
checkpointing = definitions.CheckpointingConfig(
    enabled=True,
    volume_size_gib=500,
)
```

<ParamField type="boolean">
  Set to `true` to mount a persistent checkpoint volume.
</ParamField>

<ParamField type="string">
  Override the default checkpoint directory path.
</ParamField>

<ParamField type="integer">
  Size of the checkpoint volume in GiB. Defaults to a platform-managed size.
</ParamField>

### CacheConfig

Enables a persistent read-write cache that survives across jobs. Use the cache for pip packages, downloaded model weights, preprocessed datasets, or any data you don't want to re-download on every run. When `enabled` is true, Baseten mounts two shared directories into the container. When `require_cache_affinity` is true (the default), Baseten schedules the job on a node that already has cached data, which avoids cold starts. See the [cache guide](/training/concepts/cache) for usage patterns.

```python config.py theme={"system"}
cache = definitions.CacheConfig(
    enabled=True,
    require_cache_affinity=True,
)
```

When enabled, Baseten exports two cache directories as environment variables.

| Environment variable    | Description                                                                                                                      |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `$BT_PROJECT_CACHE_DIR` | Shared across all jobs in the same [TrainingProject](#trainingproject). Use for project-specific datasets or compiled artifacts. |
| `$BT_TEAM_CACHE_DIR`    | Shared across all jobs in the same team. Use for common model weights or shared libraries.                                       |

<ParamField type="boolean">
  Set to `true` to mount persistent cache volumes.
</ParamField>

<ParamField type="boolean">
  Mount the Hugging Face cache at the legacy path for backward compatibility.
</ParamField>

<ParamField type="boolean">
  Schedule the job on a node with existing cached data when possible.
</ParamField>

<ParamField type="string">
  Base path where Baseten mounts cache directories. Defaults to `/root/.cache`.
</ParamField>

### LoadCheckpointConfig

Downloads checkpoints from previous training jobs into the container before `start_commands` run. Use this to resume training from a saved state or to initialize weights from an earlier experiment. Baseten downloads the specified checkpoints to `download_folder` (also exported as `$BT_LOAD_CHECKPOINT_DIR`) and your training script reads them at startup. For more information, see the [loading checkpoints](/training/loading) walkthrough.

```python config.py theme={"system"}
load_config = definitions.LoadCheckpointConfig(
    enabled=True,
    download_folder="/tmp/loaded_checkpoints",
    checkpoints=[
        definitions.BasetenCheckpoint.from_latest_checkpoint(project_name="my-project"),
        definitions.BasetenCheckpoint.from_named_checkpoint(
            checkpoint_name="checkpoint-24",
            job_id="abc123",
        )
    ]
)
```

<ParamField type="boolean">
  Set to `true` to download checkpoints before `start_commands` run.
</ParamField>

<ParamField type="BasetenCheckpoint[]">
  One or more checkpoint references to download. Create references with `BasetenCheckpoint.from_latest_checkpoint()` or `BasetenCheckpoint.from_named_checkpoint()`. For more information, see [BasetenCheckpoint](#basetencheckpoint).
</ParamField>

<ParamField type="string">
  Directory where Baseten downloads checkpoints. Exported as `$BT_LOAD_CHECKPOINT_DIR`. Defaults to `/tmp/loaded_checkpoints`.
</ParamField>

### BasetenCheckpoint

Creates references to checkpoints saved by previous training jobs. Pass these references to [LoadCheckpointConfig](#loadcheckpointconfig) to download checkpoint data into your container at job start. You can reference checkpoints by project name (gets the most recent), by job ID (gets the most recent from that job), or by exact checkpoint name and job ID.

```python config.py theme={"system"}
latest = definitions.BasetenCheckpoint.from_latest_checkpoint(
    project_name="my-fine-tuning-project"
)

specific = definitions.BasetenCheckpoint.from_named_checkpoint(
    checkpoint_name="checkpoint-100",
    job_id="abc123",
)

runtime = definitions.Runtime(
    start_commands=["python train.py"],
    load_checkpoint_config=definitions.LoadCheckpointConfig(
        enabled=True,
        checkpoints=[latest, specific],
    )
)
```

#### from\_latest\_checkpoint

Returns a reference to the most recent checkpoint from a project or job. At least one of `project_name` or `job_id` is required.

```python theme={"system"}
BasetenCheckpoint.from_latest_checkpoint(
    project_name: Optional[str] = None,
    job_id: Optional[str] = None,
)
```

<ParamField type="string">
  Project name to get the latest checkpoint from.
</ParamField>

<ParamField type="string">
  Job ID to get the latest checkpoint from.
</ParamField>

#### from\_named\_checkpoint

Returns a reference to a specific checkpoint by its name and job ID.

```python theme={"system"}
BasetenCheckpoint.from_named_checkpoint(
    checkpoint_name: str,
    job_id: str,
)
```

<ParamField type="string">
  Checkpoint name.
</ParamField>

<ParamField type="string">
  Job ID.
</ParamField>

## Workspace

Controls which local files Baseten uploads to the training container. By default, Baseten archives the directory containing your `config.py` (or the `source_dir` you pass to [push](#push)) and extracts it into the container's working directory. Use `Workspace` to customize this behavior: exclude large data directories, include files from outside the root, or change the root entirely.

```python config.py theme={"system"}
training_job = definitions.TrainingJob(
    image=definitions.Image(base_image="pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime"),
    workspace=definitions.Workspace(
        exclude_dirs=["data", ".git"],
    ),
)
```

### Parameters

<ParamField type="string">
  Override the root directory to archive. Defaults to the config file's parent directory.
</ParamField>

<ParamField type="string[]">
  Additional directories outside `workspace_root` to include in the upload.
</ParamField>

<ParamField type="string[]">
  Directories to exclude from the upload (for example, `"data"`, `".git"`, `"__pycache__"`).
</ParamField>

## InteractiveSession

Enables interactive access to the training container for live debugging. Configure `session_provider` to choose between [VS Code and Cursor remote tunnels](/training/interactive-sessions) and [SSH](/training/ssh), and `trigger` to control when the session starts.

<Tabs>
  <Tab title="SSH">
    ```python config.py theme={"system"}
    from truss_train import definitions
    from truss_train.definitions import (
        InteractiveSession,
        InteractiveSessionTrigger,
        InteractiveSessionProvider,
    )
    from truss.base import truss_config

    training_job = definitions.TrainingJob(
        image=definitions.Image(base_image="pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime"),
        compute=definitions.Compute(
            accelerator=truss_config.AcceleratorSpec(accelerator="H200", count=2),
        ),
        runtime=definitions.Runtime(
            start_commands=["chmod +x ./run.sh && ./run.sh"],
        ),
        interactive_session=InteractiveSession(
            trigger=InteractiveSessionTrigger.ON_FAILURE,
            session_provider=InteractiveSessionProvider.SSH,
        ),
    )
    ```

    See the [SSH guide](/training/ssh) for setup and connection instructions.
  </Tab>

  <Tab title="VS Code & Cursor">
    ```python config.py theme={"system"}
    from truss_train import definitions
    from truss_train.definitions import (
        InteractiveSession,
        InteractiveSessionTrigger,
        InteractiveSessionProvider,
        InteractiveSessionAuthProvider,
    )
    from truss.base import truss_config

    training_job = definitions.TrainingJob(
        image=definitions.Image(base_image="pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime"),
        compute=definitions.Compute(
            accelerator=truss_config.AcceleratorSpec(accelerator="H200", count=2),
        ),
        runtime=definitions.Runtime(
            start_commands=["chmod +x ./run.sh && ./run.sh"],
        ),
        interactive_session=InteractiveSession(
            trigger=InteractiveSessionTrigger.ON_FAILURE,
            timeout_minutes=-1,
            session_provider=InteractiveSessionProvider.VS_CODE,
            auth_provider=InteractiveSessionAuthProvider.GITHUB,
        ),
    )
    ```

    See the [VS Code and Cursor guide](/training/interactive-sessions) for connection instructions.
  </Tab>
</Tabs>

### Parameters

<ParamField type="InteractiveSessionTrigger">
  Controls when to activate the session. Defaults to `ON_DEMAND`.

  Available options:

  * `ON_STARTUP`: active from job start.
  * `ON_FAILURE`: activates when training exits with a non-zero code.
  * `ON_DEMAND`: activates when you connect (SSH) or authenticate through the device code flow (remote tunnel), or when you change the trigger on a running job.
</ParamField>

<ParamField type="integer">
  Minutes before the session expires. Set to `-1` to extend the expiry to 10 years. For remote tunnel sessions, the expiry resets on every reconnect. For SSH, the expiry is set once at session start.
</ParamField>

<ParamField type="InteractiveSessionProvider">
  Connection method for the interactive session. Defaults to `VS_CODE`.

  Available options:

  * `VS_CODE`: VS Code Remote Tunnels.
  * `CURSOR`: Cursor Remote Tunnels.
  * `SSH`: Direct SSH access from your terminal. See the [SSH guide](/training/ssh) for setup.
</ParamField>

<ParamField type="InteractiveSessionAuthProvider">
  Authentication provider for the remote tunnel device code flow. Defaults to `MICROSOFT`. Ignored when `session_provider=SSH`.

  Available options:

  * `GITHUB`: authenticate through GitHub.
  * `MICROSOFT`: authenticate through Microsoft.
</ParamField>

***

## Environment variables

Baseten automatically injects these environment variables into every training container. Your training script can read them to discover job metadata, locate scratch, checkpoint, and cache directories, and coordinate across nodes in [multi-node jobs](/training/concepts/multinode).

### Standard variables

| Variable                   | Description                                                                                                | Example                         |
| -------------------------- | ---------------------------------------------------------------------------------------------------------- | ------------------------------- |
| `BT_TRAINING_JOB_ID`       | Training job ID.                                                                                           | `"gvpql31"`                     |
| `BT_TRAINING_PROJECT_ID`   | Training project ID.                                                                                       | `"aghi527"`                     |
| `BT_TRAINING_JOB_NAME`     | Training job name.                                                                                         | `"gpt-oss-20b-lora"`            |
| `BT_TRAINING_PROJECT_NAME` | Training project name.                                                                                     | `"gpt-oss-finetunes"`           |
| `BT_NUM_GPUS`              | Number of GPUs per node.                                                                                   | `"4"`                           |
| `BT_WORKING_DIR`           | Container working directory. Set when [`enable_baseten_workdir`](#param-enable-baseten-workdir) is `True`. | `"/b10/workspace"`              |
| `BT_SCRATCH_DIR`           | Ephemeral scratch directory backed by local NVMe storage. Cleared when the job completes.                  | `"/mnt/bt-scratch"`             |
| `BT_CHECKPOINT_DIR`        | Checkpoint save directory.                                                                                 | `"/mnt/ckpts"`                  |
| `BT_LOAD_CHECKPOINT_DIR`   | Loaded checkpoints directory.                                                                              | `"/tmp/loaded_checkpoints"`     |
| `BT_PROJECT_CACHE_DIR`     | Project-level cache directory.                                                                             | `"/root/.cache/user_artifacts"` |
| `BT_TEAM_CACHE_DIR`        | Team-level cache directory.                                                                                | `"/root/.cache/team_artifacts"` |
| `BT_RW_CACHE_DIR`          | Base read-write cache directory.                                                                           | `"/root/.cache"`                |
| `BT_RETRY_COUNT`           | Job retry attempt count.                                                                                   | `"0"`                           |

### Multi-node variables

For distributed training across multiple nodes:

| Variable         | Description                    | Example      |
| ---------------- | ------------------------------ | ------------ |
| `BT_GROUP_SIZE`  | Number of nodes in deployment. | `"2"`        |
| `BT_LEADER_ADDR` | Leader node address.           | `"10.0.0.1"` |
| `BT_NODE_RANK`   | Node rank (0 for leader).      | `"0"`        |

***

## Deploy checkpoints

Deploys trained model checkpoints from a completed training job to Baseten's inference platform. Baseten downloads the checkpoint weights, packages them with a serving runtime, and creates a deployable model endpoint. See the [deployment guide](/training/deployment) for the full workflow.

### Deploy with CLI wizard

Deploy checkpoints interactively with the CLI wizard:

```bash theme={"system"}
uvx truss train deploy_checkpoints --job-id <job_id>
```

The wizard guides you through selecting checkpoints and configuring deployment. Baseten automatically recognizes checkpoints for full fine-tunes and LoRAs for LLMs and Whisper models.

<Note>
  The `deploy_checkpoints` command doesn't support FSDP checkpoints. Configure these manually in the Truss config.
</Note>

<Note>
  For optimized inference with TensorRT-LLM, see [Deploy with optimized inference engines](/training/deploy-with-engine-builder).
</Note>

### Deploy with static configuration

Create a Python config file for repeatable deployments:

```bash theme={"system"}
uvx truss train deploy_checkpoints --config <path_to_config_file>
```

## DeployCheckpointsConfig

Defines how to deploy checkpoints from a completed training job to a Baseten inference endpoint. Baseten reads the checkpoint weights, selects the correct serving backend based on the model weights format (full, LoRA, or Whisper), and provisions the specified [Compute](#compute) resources.

```python deploy_config.py theme={"system"}
from truss_train import definitions
from truss.base import truss_config

deploy_config = definitions.DeployCheckpointsConfig(
    model_name="fine-tuned-llm",
    checkpoint_details=definitions.CheckpointList(
        base_model_id="meta-llama/Llama-3.1-8B-Instruct",
        checkpoints=[
            definitions.LoRACheckpoint(
                training_job_id="gvpql31",
                checkpoint_name="checkpoint-100",
                lora_details=definitions.LoRADetails(rank=16),
            )
        ]
    ),
    compute=definitions.Compute(
        accelerator=truss_config.AcceleratorSpec(
            accelerator=truss_config.Accelerator.H200,
            count=1,
        )
    ),
)
```

### Parameters

<ParamField type="CheckpointList">
  Checkpoints to deploy, including the base model ID for LoRA and one or more checkpoint references. For more information, see [CheckpointList](#checkpointlist).
</ParamField>

<ParamField type="string">
  Name for the deployed model in the Baseten dashboard.
</ParamField>

<ParamField type="DeployCheckpointsRuntime">
  Environment variables for the inference runtime, such as API keys or serving configuration. For more information, see [DeployCheckpointsRuntime](#deploycheckpointsruntime).
</ParamField>

<ParamField type="Compute">
  GPU and memory allocation for the inference endpoint. Uses the same [Compute](#compute) configuration as training jobs.
</ParamField>

### DeployCheckpointsRuntime

Sets environment variables for the deployed inference endpoint. Use this to inject API keys or configuration that the serving runtime needs.

<ParamField type="object">
  Key-value pairs that Baseten injects as env vars. Use [SecretReference](#secretreference) for sensitive values.
</ParamField>

### CheckpointList

Groups one or more checkpoints for deployment. For LoRA deployments, set `base_model_id` to the Hugging Face model ID you trained the adapters on.

<ParamField type="string">
  Directory where Baseten downloads checkpoint files during deployment. Defaults to `/tmp/training_checkpoints`.
</ParamField>

<ParamField type="string">
  Hugging Face model ID for the base model. Required for LoRA deployments.
</ParamField>

<ParamField type="Checkpoint[]">
  One or more [FullCheckpoint](#fullcheckpoint), [LoRACheckpoint](#loracheckpoint), or [WhisperCheckpoint](#whispercheckpoint) instances.
</ParamField>

<ParamField type="string[]">
  Trainer checkpoint IDs to deploy. Use this when deploying checkpoints produced by a trainer rather than a training job. Mutually exclusive with `checkpoints`: set one or the other, not both.
</ParamField>

### Checkpoint types

Baseten supports three checkpoint types. Use the type that matches how your model was trained.

#### FullCheckpoint

Deploys a complete set of model weights from a full fine-tune.

<ParamField type="string">
  Training job ID.
</ParamField>

<ParamField type="string">
  Checkpoint name.
</ParamField>

<ParamField type="string">
  Auto-set to `full`.
</ParamField>

#### LoRACheckpoint

Deploys LoRA adapter weights on top of the base model you specify in [CheckpointList](#checkpointlist).

<ParamField type="string">
  Training job ID.
</ParamField>

<ParamField type="string">
  Checkpoint name.
</ParamField>

<ParamField type="string">
  Auto-set to `lora`.
</ParamField>

<ParamField type="LoRADetails">
  LoRA adapter configuration. Set `rank` to match the rank you used during training. Defaults to `LoRADetails()`. Valid values:

  * 8, 16, 32, 64, 128, 256, 320, 512.

  For more information, see [LoRADetails](#loradetails).
</ParamField>

#### WhisperCheckpoint

Deploys fine-tuned Whisper model weights for speech-to-text inference.

<ParamField type="string">
  Training job ID.
</ParamField>

<ParamField type="string">
  Checkpoint name.
</ParamField>

<ParamField type="string">
  Auto-set to `whisper`.
</ParamField>

### LoRADetails

Sets the LoRA rank for adapter deployment. The rank must match the rank you set during training.

<ParamField type="integer">
  LoRA rank. Valid values: 8, 16, 32, 64, 128, 256, 320, 512.
</ParamField>
