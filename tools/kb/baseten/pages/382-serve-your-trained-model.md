# Serve your trained model
Source: https://docs.baseten.co/training/deployment

How to deploy checkpoints from Baseten Training jobs as usable models.

Once your `TrainingJob` has produced checkpoints, you can deploy them as model endpoints.

**This feature works with HuggingFace-compatible LLMs.**

<Note>
  For optimized inference performance with TensorRT-LLM, BEI and Baseten Inference Stack, see [Deploy with optimized inference engines](/training/deploy-with-engine-builder).
</Note>

To deploy checkpoints, first ensure you have a `TrainingJob` that's running with a `checkpointing_config` enabled.

```python theme={"system"}
runtime = definitions.Runtime(
    start_commands=[
        "/bin/sh -c './run.sh'",
    ],
    checkpointing_config=definitions.CheckpointingConfig(
        enabled=True,
    ),
)
```

In your training code or configuration, ensure that your checkpoints are being written to the checkpointing directory, which can be referenced through [`$BT_CHECKPOINT_DIR`](/reference/sdk/training#baseten-provided-environment-variables).
The contents of this directory are uploaded to Baseten's storage and made immediately available for deployment.
*(You can optionally specify a `checkpoint_path` in your `checkpointing_config` if you prefer to write to a specific directory).* The default location is "/tmp/training\_checkpoints".

To deploy your checkpoint(s) as a `Deployment`, you can:

### CLI Deployment

```bash theme={"system"}
truss train deploy_checkpoints [OPTIONS]
```

**Options:**

| Option                      | Type | Description                                                                                                                                                             |
| --------------------------- | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--job-id`                  | TEXT | Job ID to deploy checkpoints from. If not specified, deploys from the most recent training job.                                                                         |
| `--project`                 | TEXT | Project name or project ID.                                                                                                                                             |
| `--project-id`              | TEXT | Project ID.                                                                                                                                                             |
| `--trainer-id`              | TEXT | Trainer ID. Deploy checkpoints from a trainer instead of a training job. Mutually exclusive with `--project`, `--project-id`, and `--job-id`.                           |
| `--config`                  | TEXT | Path to a Python file that defines a `DeployCheckpointsConfig` (see [Advanced CLI Deployment](#advanced-cli-deployment)).                                               |
| `--dry-run`                 | FLAG | Generate a Truss config without deploying. Useful for inspecting or customizing the config before deployment.                                                           |
| `--truss-config-output-dir` | TEXT | Path to output the Truss config to. Defaults to `truss_configs/<model_version_name>_<model_version_id>`, or `truss_configs/dry_run_<timestamp>` when using `--dry-run`. |
| `--remote`                  | TEXT | Remote to use.                                                                                                                                                          |

This will deploy the most recent checkpoint from your training job as an inference endpoint.

### UI Deployment

You can also deploy checkpoints directly from the Baseten UI by pressing the dropdown menu on your completed training job and selecting "Deploy" on your selected checkpoint.

### Advanced CLI Deployment

You can also:

* run `truss train deploy_checkpoints [--job-id <job_id>]` and follow the setup wizard.
* define an instance of a `DeployCheckpointsConfig` class (this is helpful for small changes that aren't provided by the wizard) and run `truss train deploy_checkpoints --config <path_to_config_file>`.

When `deploy_checkpoints` is run, `truss` will construct a deployment `config.yml` and store it on disk. By default, the config is written to `truss_configs/<model_version_name>_<model_version_id>`. You can control the output location with `--truss-config-output-dir`.

To inspect or customize the config before deploying, use `--dry-run` to generate the config without deploying:

```bash theme={"system"}
truss train deploy_checkpoints --job-id <job_id> --dry-run
```

If you'd like to modify the resulting deployment config, you can copy it into a permanent directory and customize it as needed.

This file defines the source of truth for the deployment and can be deployed independently with `truss push`. See [deployments](../deployment/deployments) for more details.

You can also reference training checkpoints using the `bt://` URI scheme in your [weights configuration](/development/model/bdn#baseten-training).

After successful deployment, your model will be deployed on Baseten, where you can run inference requests and evaluate performance. See [Calling Your Model](/inference/calling-your-model) for more details.

To download the files you saved to the checkpointing directory or understand the file structure, you can run `truss train get_checkpoint_urls [--job-id=<job_id>]` to get a JSON file containing presigned URLs for each training job.

The JSON file contains the following structure:

```json theme={"system"}
{
  "timestamp": "2025-06-23T13:44:16.485905+00:00",
  "job": {
    "id": "03yv1l3",
    "created_at": "2025-06-18T14:30:30.480Z",
    "current_status": "TRAINING_JOB_COMPLETED",
    "error_message": null,
    "instance_type": {
			"id": "H200:2x8x128x1600",
			"name": "H200:2x8x128x1600 - 2 Nodes of 8 H200 GPUs, 1128 GiB VRAM, 128 vCPUs, 1600 GiB RAM",
			"memory_limit_mib": 1650000,
			"millicpu_limit": 127900,
			"gpu_count": 8,
			"gpu_type": "H200",
			"gpu_memory_limit_mib": 1155072
		},
    "updated_at": "2025-06-18T14:30:30.510Z",
    "training_project_id": "lqz9o34",
    "training_project": {
      "id": "lqz9o34",
      "name": "checkpointing"
    }
  },
  "checkpoint_artifacts": [
    {
      "url": "https://bt-training-eqwnwwp-f815d6cd-19bf-4589-bfcb-da76cd8432c0.s3.amazonaws.com/training_projects/lqz9o34/jobs/03yv1l3/rank-0/checkpoint-24/tokenizer_config.json?AWSAccessKeyId=EXAMPLE_ACCESS_KEY_ID&Signature=example-signature&Expires=1234567890",
      "relative_file_name": "checkpoint-24/tokenizer_config.json",
      "node_rank": 0
    }
    ...
  ]
}
```

**Important notes about the presigned URLs:**

* The presigned URLs expire after **7 days** from generation
* These URLs are primarily intended for **evaluation and testing purposes**, not for long-term inference deployments
* For production deployments, consider copying the checkpoint files to your Truss model directory and downloading them in the model's `load()` function

## Complex and custom use cases

* Custom Model Architectures
* Weights Sharded Across Nodes

Examine the structure of your files with `truss train get_checkpoint_urls --job-id=<your-training-job-id>`. If a file looks like this:

```json theme={"system"}
{
  "url": "https://bt-training-eqwnwwp-f815d6cd-19bf-4589-bfcb-da76cd8432c0.s3.amazonaws.com/training_projects/lqz9o34/jobs/03yv1l3/rank-4/checkpoint-10/weights.safetensors?AWSAccessKeyId=EXAMPLE_ACCESS_KEY_ID&Signature=example-signature&Expires=1234567890",
  "relative_file_name": "checkpoint-10/weights.safetensors",
  "node_rank": 4
}
```

In your Truss configuration, add a section like this: Wildcards `*` match to an arbitrary number of chars while `?` matches to one.

```yaml theme={"system"}
training_checkpoints:
  download_folder: /tmp/training_checkpoints
  artifact_references:
    - training_job_id: <your-training-job-id>
      paths:
        - rank-*/checkpoint-10/ # Pull in all the files for checkpoint-10 across all nodes
```

When your model replica starts up, you can read the file from the path `/tmp/training_checkpoints/rank-[node-rank]/[relative_file_name]`. For the example above, the file can be read from:

```
/tmp/training_checkpoints/<your-training-job-id>/rank-4/checkpoint-10/weights.safetensors
```
