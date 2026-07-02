# Slurm workstations
Source: https://docs.baseten.co/training/slurm

Launch a multi-node Slurm cluster on Baseten training infrastructure with a single CLI command.

One command gives you a private [Slurm](https://slurm.schedmd.com/) cluster on Baseten training infrastructure. `truss train workstation --node-count N` provisions N full nodes, bootstraps Slurm across them, and prints the SSH command to connect. Every node runs `slurmd`, the rank-0 node also runs `slurmctld` as the controller, and each node's GPUs register as `gres` automatically.

For single-node workstations, see [SSH access](/training/ssh). For non-interactive multi-node training jobs, see [Multinode training](/training/concepts/multinode).

## How Baseten builds the cluster

When `--node-count` is greater than 1, every node runs a Slurm bootstrap at startup:

1. Each node installs Slurm and munge, then detects its GPUs.
2. Nodes coordinate through the shared project cache, registering themselves until all `BT_GROUP_SIZE` nodes are present.
3. The rank-0 node generates `/etc/slurm/slurm.conf` and distributes it: cluster name `workstation`, a single default partition named `gpu` with no time limit, and each node's GPUs registered as `gres`.
4. The controller starts `slurmctld` and `slurmd`; workers start `slurmd`. The controller is also a compute node, so all N nodes accept work.

Every node ends up with the same `slurm.conf` and munge key, so Slurm commands work from any node. For the environment variables Baseten injects (`BT_NODE_RANK`, `BT_GROUP_SIZE`, `BT_PROJECT_CACHE_DIR`, and more), see the [SDK reference](/reference/sdk/training#baseten-provided-environment-variables).

## Launch a workstation

First, set up SSH access if you haven't:

```bash theme={"system"}
uvx truss ssh setup
```

Then launch a multi-node workstation:

```bash theme={"system"}
uvx truss train workstation --node-count 2 --accelerator H100
```

* `--node-count` provisions full nodes, using all GPUs on each. It's mutually exclusive with `--gpu-count`, which configures single-node workstations.
* `--accelerator` selects the GPU type (H100 by default).
* `--image` swaps the base image (default `nvidia/cuda:12.8.1-devel-ubuntu24.04`). The Slurm bootstrap installs its own packages, so any Debian-based image with your framework preinstalled works.

See the [CLI reference](/reference/cli/training/training-cli#workstation) for all options. Once the cluster is up, connect using the SSH command printed in the output.

The cluster lives until you stop the workstation, and nodes [bill per minute](/organization/billing) while up. Stop it with `truss train stop` when you finish; that tears down Slurm and releases the nodes.

## Verify the cluster

After connecting, confirm the cluster sees every node and GPU:

```bash theme={"system"}
sinfo
```

```output theme={"system"}
PARTITION AVAIL  TIMELIMIT  NODES  STATE NODELIST
gpu*         up   infinite      2   idle node-[0-1]
```

Run a command across all nodes through the scheduler:

```bash theme={"system"}
srun --nodes=2 hostname
```

```output theme={"system"}
node-0
node-1
```

Check that each node registered its GPUs:

```bash theme={"system"}
scontrol show nodes | grep -E "NodeName|Gres"
```

```output theme={"system"}
NodeName=node-0 ...
   Gres=gpu:8
NodeName=node-1 ...
   Gres=gpu:8
```

To confirm which node your SSH session landed on, run `echo $BT_NODE_RANK`; rank 0 is the controller.

## Run distributed work

The project cache directory is shared across all nodes. Put your code, data, and outputs there so every rank sees the same files:

```bash theme={"system"}
cd $BT_PROJECT_CACHE_DIR
git clone https://github.com/basetenlabs/ml-cookbook.git
```

Launch interactively with `srun`:

```bash theme={"system"}
srun --nodes=2 --ntasks-per-node=1 --gres=gpu:$BT_NUM_GPUS python train.py
```

Or create `pretrain.sbatch` on the shared cache:

```bash theme={"system"}
#!/bin/bash
#SBATCH --job-name=pretrain
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --chdir=/root/.cache/user_artifacts
#SBATCH --output=%x-%j.log

srun python train.py
```

`#SBATCH` lines don't expand environment variables, so `--chdir` uses the literal path that `$BT_PROJECT_CACHE_DIR` resolves to (`/root/.cache/user_artifacts`). Pass the GPU count on the command line instead, where `$BT_NUM_GPUS` expands. Submit the job and track it:

```bash theme={"system"}
sbatch --gres=gpu:$BT_NUM_GPUS pretrain.sbatch
squeue
```

```output theme={"system"}
Submitted batch job 1
JOBID PARTITION     NAME USER ST  TIME NODES NODELIST(REASON)
    1       gpu pretrain root  R  0:07     2 node-[0-1]
```

Slurm sets the usual `SLURM_*` environment variables (`SLURM_NODEID`, `SLURM_NTASKS`, `SLURM_JOB_NODELIST`), so distributed launchers like `torchrun` pick up the topology the standard way. For job arrays, dependencies, and everything beyond launching, see the [Slurm documentation](https://slurm.schedmd.com/documentation.html).

## Checkpoints and the shared cache

Workstations support the same storage as training jobs:

* The shared cache mounts on every node and persists across workstation restarts within a project. See [Cache](/training/concepts/cache).
* Pass `--enable-checkpointing` (with optional `--checkpoint-path` and `--checkpoint-volume-size`) to mount checkpoint storage, and `--checkpoint-from-job` to load the latest checkpoint from a previous job. See [Checkpoints](/training/concepts/checkpoints).

## Notes and limits

* Everything runs as root, and there is one partition. The bootstrap regenerates `slurm.conf` on every start, so manual edits don't survive a restart.
* Multi-node workstations always allocate full nodes; there is no fractional multi-node sizing.

## Next steps

Once your training script behaves across nodes, the same project can run it as a non-interactive multi-node training job, with the cache and checkpoints carrying over.

<CardGroup>
  <Card title="SSH access" href="/training/ssh">
    Single-node workstations and direct SSH connections.
  </Card>

  <Card title="VS Code & Cursor" href="/training/interactive-sessions">
    Attach your IDE to a workstation with remote tunnels.
  </Card>

  <Card title="Multinode training" href="/training/concepts/multinode">
    Non-interactive distributed training jobs.
  </Card>

  <Card title="CLI reference" href="/reference/cli/training/training-cli#workstation">
    All `truss train workstation` options.
  </Card>
</CardGroup>
