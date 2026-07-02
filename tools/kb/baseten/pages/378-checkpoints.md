# Checkpoints
Source: https://docs.baseten.co/training/concepts/checkpoints

Learn how to use Baseten's checkpointing feature to manage model checkpoints and avoid disk errors during training.

With checkpointing enabled, you can manage your model checkpoints seamlessly and avoid common training issues.

## Benefits of checkpointing

* **Avoid catastrophic out of disk errors**: We mount additional storage at the checkpointing directory to help avoid out of disk errors during your training run.
* **Maximize GPU utilization**: When checkpointing is enabled, any data written to the checkpointing directory will be uploaded to the cloud by a separate process, allowing you to maximize GPU time spent training.
* **Seamless checkpoint management**: Checkpoints are automatically uploaded to cloud storage for easy access and management.

## Enable checkpointing

To enable checkpointing, add a `CheckpointingConfig` to the `Runtime` and set `enabled` to `True`:

```python theme={"system"}
from truss_train import definitions

training_runtime = definitions.Runtime(
    # ... other configuration options
    checkpointing_config=definitions.CheckpointingConfig(enabled=True)
)
```

## Use the checkpoint directory

Baseten will automatically export the [`$BT_CHECKPOINT_DIR`](/reference/sdk/training#baseten-provided-environment-variables) environment variable in your job's environment.

<Danger>
  **Write your checkpoints to the `$BT_CHECKPOINT_DIR` directory so Baseten can automatically backup and preserve them.**
</Danger>

## Browse checkpoints

Use the CLI to list and interactively explore checkpoint files for a job:

```sh theme={"system"}
truss train checkpoints list --job-id abc123
```

In interactive mode, you can fuzzy-search checkpoints, navigate their directory tree, and inspect file contents, including tensor summaries for `.safetensors` files. See [`checkpoints list`](/reference/cli/training/training-cli#checkpoints-list) for all options.

## Resume training from a checkpoint

To resume training from a saved checkpoint or initialize a new job from a previous run, configure a `LoadCheckpointConfig` on the `Runtime`. Baseten downloads the referenced checkpoints into `$BT_LOAD_CHECKPOINT_DIR` before your `start_commands` run:

```python theme={"system"}
from truss_train import definitions

load_checkpoint_config = definitions.LoadCheckpointConfig(
    enabled=True,
    checkpoints=[
        definitions.BasetenCheckpoint.from_latest_checkpoint(
            project_name="my-training-project",
        ),
    ],
)
```

For more information, see [loading checkpoints](/training/loading).

## Serve checkpoints

Serve your model checkpoints using Baseten's serving infrastructure. Reference training checkpoints in your [weights configuration](/development/model/bdn#baseten-training) using the `bt://` URI scheme. See [serving checkpoints](/training/deployment) for deployment details.

<Warning>
  When you delete a job or project, all undeployed checkpoints are permanently deleted with no archival or recovery option. Deployed checkpoints aren't affected. See [Management](/training/management) for details.
</Warning>
