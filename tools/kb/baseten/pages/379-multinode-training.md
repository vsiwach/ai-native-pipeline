# Multinode training
Source: https://docs.baseten.co/training/concepts/multinode

Learn how to configure and run multinode training jobs with Baseten Training.

Baseten Training supports multinode training over infiniband for distributed training across multiple nodes.

## Configure multinode training

To deploy a multinode training job:

* Configure the `Compute` resource in your `TrainingJob` by setting the `node_count` to the number of nodes you'd like to use (for example, 2).

```python theme={"system"}
from truss_train import definitions

compute = definitions.Compute(
    node_count=2,  # Use 2 nodes for multinode training
    # ... other compute configuration options
)
```

## Environment variables

Make sure you've properly integrated with the
[Baseten provided environment variables](/reference/sdk/training#baseten-provided-environment-variables)
for distributed training.

## Network configuration

Baseten provides high-speed infiniband networking between nodes to ensure efficient communication during distributed training. This enables:

* Fast gradient synchronization.
* Efficient parameter updates.
* Low-latency communication between nodes.

## Checkpointing in multinode training

Checkpointing behavior varies across training frameworks in multinode setups. One common pattern is to use the shared cache directory that all nodes can access:

```bash theme={"system"}
# Use shared volume with job name for checkpointing
ckpt_dir="${BT_PROJECT_CACHE_DIR}/${BT_TRAINING_JOB_NAME}"
```

Then ensure you write to `ckpt_dir`. This ensures all nodes write to the same checkpoint location. For comprehensive framework-specific examples and patterns, see the [Training Cookbook](https://github.com/basetenlabs/ml-cookbook).
Keep in mind that these checkpoints will not be backed up by Baseten since they are not stored in \$BT\_CHECKPOINT\_DIR. Make sure to copy them there at some point to ensure they are preserved.

## Common practices

When setting up multinode training:

1. **Data loading**: Ensure your data loading is properly distributed across nodes.
2. **Seeding**: Use consistent seeding across all nodes for reproducible results.
3. **Monitoring**: Monitor training metrics across all nodes to ensure balanced training.

## Interactive multi-node clusters

For interactive multi-node work, `truss train workstation --node-count N` provisions the same multi-node compute as an SSH workstation with a Slurm cluster bootstrapped across the nodes. See [Slurm workstations](/training/slurm).
