# Storage and data ingestion
Source: https://docs.baseten.co/training/concepts/storage

Load model weights and training data into Baseten training containers through BDN, S3, Hugging Face, and GCS.

Training jobs need model weights, training datasets, and configuration files.
Baseten provides multiple ways to get data into your training container, from
cached delivery through
[Baseten Delivery Network (BDN)](/development/model/bdn) to direct downloads in
your training script.

## Load weights and data with BDN

Use the [`weights`](/reference/sdk/training#weightssource) parameter on
[`TrainingJob`](/reference/sdk/training#trainingjob) to mount model weights and
training data into your container through BDN. BDN mirrors your data once and
serves it from multi-tier caches, so subsequent jobs start faster.

<Note>
  BDN mirrors your weights to Baseten storage during the `CREATED` state, before any compute is provisioned. Once your job is scheduled on a node, BDN places the weights on local disk before your `start_commands` run. Weight delivery never overlaps with workload execution, so BDN has no effect on training throughput. The only difference between a cache hit and a cache miss is how long the deploy phase takes.
</Note>

Each weight source specifies a remote URI and a local mount path. When your
container starts, the data is already available at the `mount_location`. No
download code needed in your training script.

### Hugging Face and S3 example

Load model weights from Hugging Face and training data from S3, mounted into the training container before your code runs:

```python config.py theme={"system"}
from truss_train import TrainingProject, TrainingJob, Image, Compute, Runtime, WeightsSource
from truss.base.truss_config import AcceleratorSpec

training_job = TrainingJob(
    image=Image(base_image="pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime"),
    compute=Compute(
        accelerator=AcceleratorSpec(accelerator="H200", count=1),
    ),
    runtime=Runtime(
        start_commands=["python train.py"],
    ),
    weights=[
        WeightsSource(
            source="hf://Qwen/Qwen3-0.6B",
            mount_location="/app/models/Qwen/Qwen3-0.6B",
        ),
        WeightsSource(
            source="s3://my-bucket/training-data",
            mount_location="/app/data/training-data",
        ),
    ],
)

training_project = TrainingProject(name="qwen3-finetune", job=training_job)
```

In your training script, reference the mount paths directly:

```python train.py theme={"system"}
from transformers import AutoModelForCausalLM, AutoTokenizer

model = AutoModelForCausalLM.from_pretrained("/app/models/Qwen/Qwen3-0.6B")
tokenizer = AutoTokenizer.from_pretrained("/app/models/Qwen/Qwen3-0.6B")

# Training data is available at /app/data/training-data/
```

### Supported sources

BDN supports these URI schemes:

| Scheme  | Example                             | Description           |
| ------- | ----------------------------------- | --------------------- |
| `hf://` | `hf://meta-llama/Llama-3.1-8B@main` | Hugging Face Hub.     |
| `s3://` | `s3://my-bucket/path/to/data`       | Amazon S3.            |
| `gs://` | `gs://my-bucket/path/to/data`       | Google Cloud Storage. |
| `r2://` | `r2://account_id.bucket/path`       | Cloudflare R2.        |

For Hugging Face sources, pin to a specific revision with the `@revision` suffix (branch, tag, or commit SHA).

### Authentication

Private or gated sources require authentication.
Add an `auth` block to your `WeightsSource`:

<Tabs>
  <Tab title="Hugging Face">
    Store a [Hugging Face token](https://huggingface.co/settings/tokens) as a [Baseten secret](/development/model/secrets):

    ```python theme={"system"}
    WeightsSource(
        source="hf://meta-llama/Llama-3.1-8B@main",
        mount_location="/app/models/llama",
        auth={"auth_method": "CUSTOM_SECRET", "auth_secret_name": "hf_access_token"},
    )
    ```
  </Tab>

  <Tab title="S3 (IAM credentials)">
    Store AWS credentials as a JSON [Baseten secret](/development/model/secrets):

    ```python theme={"system"}
    WeightsSource(
        source="s3://my-bucket/training-data",
        mount_location="/app/data/training-data",
        auth={"auth_method": "CUSTOM_SECRET", "auth_secret_name": "aws_credentials"},
    )
    ```

    The secret value must contain `aws_access_key_id`, `aws_secret_access_key`, and `aws_region`.
  </Tab>
</Tabs>

For the full list of authentication options and source-specific configuration, see the [BDN configuration reference](/development/model/bdn#configuration-reference).

### Filter files

Use `allow_patterns` and `ignore_patterns` to download only the files you need:

```python theme={"system"}
WeightsSource(
    source="hf://meta-llama/Llama-3.1-8B@main",
    mount_location="/app/models/llama",
    allow_patterns=["*.safetensors", "config.json", "tokenizer.*"],
    ignore_patterns=["*.md", "*.txt"],
)
```

### How BDN serves training jobs

When you submit a training job, BDN compares your `weights` config to what's already in Baseten storage, pulls anything missing from the upstream source, and stages the full set on the node before your `start_commands` run.
Data delivery happens entirely during the `CREATED` and `DEPLOYING` phases.

Two cache tiers sit in front of Baseten's mirror:

* **Cluster-local cache:** shared across nodes in a GPU cluster. Populated the first time a job in that cluster pulls a given set of files.
* **Node-local cache:** lives on the node itself. Populated when a job lands on that node.

Both caches evict with LRU. On a **node-local hit**, the node mounts the data directly and your job starts almost immediately. On a **cluster-local hit**, BDN transfers the data from the cluster cache to the node, which adds a small amount of deploy time. On a **full miss**, BDN pulls from its mirror, which adds more deploy time. None of these affect training throughput.

### Weight access across jobs

A training job reads only the weight sources it declares in its config. Private sources like S3, GCS, and R2 stay within your organization; public Hugging Face weights are already public and can be served from a shared cache across organizations.

Within your organization, jobs that reference the same unchanged source pull from the upstream once instead of once per job. For example, running many jobs against the same S3 dataset egresses from your bucket a single time, regardless of which user launched them.

### BDN or training cache?

Use BDN for read-only inputs that are known at job start, like model weights and frozen datasets. Baseten delivers them before training begins, so you never pay for IO or compute time while they load.

Use the [training cache](/training/concepts/cache) when you need read-write storage that persists across jobs, or when one job produces data that a later job consumes. Common examples: pip package installs, compiled artifacts, and preprocessed datasets you build once and reuse.

***

## Storage types overview

Baseten Training provides four ways to move data in and out of a job:

| Storage type                                       | Persistence                                       | Use case                                                        |
| -------------------------------------------------- | ------------------------------------------------- | --------------------------------------------------------------- |
| [BDN (`weights`)](#load-weights-and-data-with-bdn) | Mirrored once; cluster- and node-local LRU caches | Read-only model weights and datasets known at job start.        |
| [Training cache](/training/concepts/cache)         | Read-write, persistent between jobs               | Pip packages, compiled artifacts, preprocessed datasets.        |
| [Checkpointing](/training/concepts/checkpoints)    | Backed up to cloud storage                        | Model checkpoints and artifacts you want to deploy or download. |
| Ephemeral storage                                  | Cleared after job completes                       | Temporary files, intermediate outputs.                          |

The training cache is scoped to a single GPU cluster. A job reuses cached data only when it runs on the cluster where that data was cached, and the cache doesn't follow you to a different cluster. For data you want available everywhere, load it through BDN, which mirrors across clusters. See [Cache scope](/training/concepts/cache#cache-scope) for how cluster affinity works.

### Ephemeral storage

Write temporary files to the `$BT_SCRATCH_DIR` directory. This path is backed by local NVMe storage on the node and is cleared when your job completes. Use it for:

* Temporary files during training.
* Intermediate outputs that don't need to persist.
* Scratch space for data processing.

```python theme={"system"}
import os

scratch = os.environ["BT_SCRATCH_DIR"]
tmp_output = os.path.join(scratch, "processed_data")
```

<Warning>
  Do not write temporary files to arbitrary paths like `/tmp` or `/root`. Always use `$BT_SCRATCH_DIR` so Baseten can manage storage across hardware configurations.
</Warning>

## Load data in your training script

When data isn't available through a BDN-supported URI scheme, download it directly in your training script.
This works well for datasets loaded from framework-specific libraries or custom download logic.

<Tabs>
  <Tab title="Amazon S3">
    Use [Baseten secrets](/organization/secrets) to authenticate to your S3 bucket.

    1. Add your AWS credentials as secrets in your Baseten account.

    2. Reference the secrets in your job configuration:

       ```python theme={"system"}
       from truss_train import definitions

       runtime = definitions.Runtime(
           environment_variables={
               "AWS_ACCESS_KEY_ID": definitions.SecretReference(name="aws_access_key_id"),
               "AWS_SECRET_ACCESS_KEY": definitions.SecretReference(name="aws_secret_access_key"),
           },
       )
       ```

    3. Download from S3 in your training script:

       ```python theme={"system"}
       import boto3

       s3 = boto3.client('s3')
       s3.download_file('my-bucket', 'training-data.tar.gz', '/path/to/local/file')
       ```

    <Tip>
      To avoid re-downloading large datasets on each job, download to the [training cache](/training/concepts/cache) and check if files exist before downloading.
    </Tip>
  </Tab>

  <Tab title="Hugging Face">
    Reference a Hugging Face dataset in your training code:

    ```python theme={"system"}
    from datasets import load_dataset

    ds = load_dataset("your-username/your-dataset", split="train")
    ```

    For private datasets, authenticate using a Hugging Face token stored in [Baseten secrets](/organization/secrets):

    ```python theme={"system"}
    runtime = definitions.Runtime(
        environment_variables={
            "HF_TOKEN": definitions.SecretReference(name="hf_access_token"),
        },
    )
    ```
  </Tab>

  <Tab title="Google Cloud Storage">
    Authenticate with [Baseten secrets](/organization/secrets) and download in your training code:

    ```python theme={"system"}
    from google.cloud import storage

    client = storage.Client()
    bucket = client.bucket('my-bucket')
    blob = bucket.blob('training-data.tar.gz')
    blob.download_to_filename('/path/to/local/file')
    ```
  </Tab>
</Tabs>

## Data size and limits

| Size   | Description               |
| ------ | ------------------------- |
| Small  | A few GBs.                |
| Medium | Up to 1 TB (most common). |
| Large  | 1-10 TB.                  |

The default training cache is 1 TB.
[Contact support](mailto:support@baseten.co) to increase the cache size for larger datasets.

## Data security

Data transfer happens within Baseten's VPC using secure connections.
Baseten doesn't share customer data across tenants. When you enable [training cache](/training/concepts/cache), data persists between jobs until you delete the project. Ephemeral storage is cleared when your job completes.
For self-hosted deployments, training can use storage buckets in your own AWS or GCP account.

To learn more and access official policies and certifications, visit the [Baseten Trust Center](https://trust.baseten.co/).

## Storage performance

Read and write speeds vary by cluster and storage configuration:

| Storage type   | Write speed         | Read speed          |
| -------------- | ------------------- | ------------------- |
| Node storage   | 1.2-1.8 GB/s        | 1.7-2.1 GB/s        |
| Training cache | 340 MB/s - 1.0 GB/s | 470 MB/s - 1.6 GB/s |

For workloads with high I/O requirements or large storage requirements, [contact support](mailto:support@baseten.co).

## Next steps

* **[BDN configuration reference](/development/model/bdn#configuration-reference)**: Full list of weight source options, authentication methods, and supported URI schemes.
* **[Cache](/training/concepts/cache)**: Persist data between jobs and speed up training iterations.
* **[Checkpointing](/training/concepts/checkpoints)**: Save and manage model checkpoints during training.
* **[Multinode training](/training/concepts/multinode)**: Scale training across multiple nodes with shared cache access.
