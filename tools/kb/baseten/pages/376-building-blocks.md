# Building blocks
Source: https://docs.baseten.co/training/concepts/basics

Learn how to get up and running on Baseten Training

This page covers the essential building blocks of Baseten Training. These are
the core concepts you'll need to understand to effectively organize and execute
your training workflows.

## How Baseten Training works

You can launch Baseten Training jobs from any terminal. Create a training job from within a directory, and Baseten packages that directory so you can push it.

This allows you to define your Baseten training config, scripts, code, and any other dependencies within the folder.

Within the folder, we require you to include a Baseten training config file such as `config.py`. The `config.py` includes a list of `start_commands`, which can be anything from running a Python file (`python train.py`) to a bash script (`chmod +x run.sh && ./run.sh`).

<Tip>
  If you're looking to upload more than 1GB of files, we strongly suggest
  uploading your data to an object store and including a download command before
  running your training code. To avoid duplicate downloads, check out our
  documentation on the [cache](/training/concepts/cache). For more information
  on storage options and data ingestion, see our [storage guide](/training/concepts/storage).
</Tip>

## Set up your workspace

If you'd like to start from one of our existing recipes, you can check out one of the following examples:

**Simple CPU job with raw PyTorch:**

```bash theme={"system"}
truss train init --examples mnist-pytorch
```

**More complex example that trains GPT-OSS-20b:**

```bash theme={"system"}
truss train init --examples oss-gpt-20b-axolotl
```

Your `config.py` contains all infrastructure configuration for your job, which we will cover below.

Your `run.sh` is invoked by the command that runs when the job first begins. Here you can install any Python dependencies not already included in your Docker image, and begin the execution of your code either by calling a Python file with your training code or a launch command.

## Organize your work with `TrainingProject`s

A `TrainingProject` is a lightweight organization tool to help you group different `TrainingJob`s together.

Your team can use `TrainingProject`s to facilitate collaboration and organization.

## Run a `TrainingJob`

Once you have a `TrainingProject`, the actual work of training a model happens within a **`TrainingJob`**. Each `TrainingJob` represents a single, complete execution of your training script with a specific configuration.

* **What it is:** A `TrainingJob` is the fundamental unit of execution. It bundles together:
  * Your training code.
  * A base `image`.
  * The `compute` resources needed to run the job.
  * The `runtime` configurations like startup commands and environment variables.
* **Why use it:** Each job is a self-contained, reproducible experiment. If you want to try training your model with a different learning rate, more GPUs, or a slightly modified script, you can create new `TrainingJob`s while knowing that previous ones have been persisted on Baseten.
* **Lifecycle:** A job progresses through several stages: creation (`TRAINING_JOB_CREATED`), resource setup (`TRAINING_JOB_DEPLOYING`), active execution (`TRAINING_JOB_RUNNING`), and a terminal state like `TRAINING_JOB_COMPLETED`. See the [Lifecycle](/training/lifecycle) page for details.

## Compute resources

The `Compute` configuration defines the computational resources your training job will use. This includes:

* **GPU specifications** - Choose from various GPU types based on your model's requirements.
* **CPU and memory** - Configure the amount of CPU and RAM allocated to your job.
* **Node count** - For single-node or multi-node training setups.

Baseten Training supports H200 and H100 GPUs. Choose your GPU type based
on your model's memory requirements and performance needs.

### CPU-only jobs

GPU allocation is optional. Omit `accelerator` from `Compute` to run a
CPU-only job, which is useful for data preparation, smoke tests, or lightweight
training workloads (such as the `mnist-pytorch` example above):

```python config.py theme={"system"}
from truss_train import definitions

compute = definitions.Compute(
    cpu_count=8,
    memory="32Gi",
)
```

CPU-only training jobs are not subject to the [16-vCPU limit that applies to
CPU-only inference deployments](/deployment/resources#cpu-only-instances). Set
`cpu_count` and `memory` to the values your workload needs. If you hit a
ceiling when requesting larger CPU or memory allocations, contact
[support@baseten.co](mailto:support@baseten.co).

## Base images

Baseten provides pre-configured base images that include common ML frameworks and dependencies. These images are optimized for training workloads and include:

* Popular ML frameworks (PyTorch, VERL, Megatron, Axolotl, etc.).
* GPU drivers and CUDA support.
* Common data science libraries.

You can also use [custom or private images](/development/model/dependencies#private-registries) if you have specific requirements.

## Securely integrate with external services with `SecretReference`

Successfully training a model often requires many tools and services. Baseten provides **`SecretReference`** for secure handling of secrets.

* **How to use it:** Store your secret (for example, an API key for Weights & Biases) in your Baseten workspace with a specific name. In your job's configuration (for example, environment variables), you refer to this secret by its name using `SecretReference`. The actual secret value is never exposed in your code.
* **How it works:** Baseten injects the secret value at runtime under the environment variable name that you specify.

```python theme={"system"}
from truss_train import definitions

runtime = definitions.Runtime(
    # ... other runtime options
    environment_variables={
        "HF_TOKEN": definitions.SecretReference(name="hf_access_token"),
    },
)
```

## Run inference on trained models

The journey from training to a usable model in Baseten typically follows this path:

1. A `TrainingJob` with checkpointing enabled, produces one or more model artifacts.
2. You run `truss train deploy_checkpoints` to deploy a model from your most recent training job. You can read more about this at [Serving Trained Models](/training/deployment).
3. Once deployed, your model will be available for inference through the API. See more at [Calling Your Model](/inference/calling-your-model).

## Next steps

Now that you understand the basics of Baseten Training, explore these advanced topics to optimize your training workflows:

* **[Cache](/training/concepts/cache)** - Speed up your training iterations by persisting data between jobs and avoiding expensive downloads.
* **[Checkpointing](/training/concepts/checkpoints)** - Manage model checkpoints seamlessly and avoid disk errors during training.
* **[Multinode training](/training/concepts/multinode)** - Scale your training across multiple nodes with high-speed infiniband networking.
