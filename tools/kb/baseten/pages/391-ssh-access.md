# SSH access
Source: https://docs.baseten.co/training/ssh

Connect to training containers directly from your terminal with standard SSH.

SSH (Secure Shell) is a protocol for encrypted, authenticated access to a remote machine. With training jobs on Baseten, you can SSH into any running job and get a full terminal inside the training container to debug, inspect files, run commands, edit code, or transfer data with `scp` and `sftp`. This gives you the same control you'd have on a local GPU box, just running on Baseten-managed hardware.

Unlike [VS Code and Cursor remote tunnels](/training/interactive-sessions), SSH is terminal-first and works with any OpenSSH-compatible tool.

## Prerequisites

<Note>
  SSH sessions must be enabled for your Baseten workspace. [Contact support](mailto:support@baseten.co) to request access.
</Note>

* **Baseten account**: [Sign up](https://app.baseten.co/) and generate an [API key](https://app.baseten.co/settings/account/api_keys).
* **[uv](https://docs.astral.sh/uv/)**: This guide uses `uvx` to run [Truss](https://pypi.org/project/truss/) commands without a separate install step. Log in to Baseten:

  ```bash theme={"system"}
  uvx truss login
  ```
* **OpenSSH client**: Pre-installed on macOS and Linux. On Windows, use the OpenSSH optional feature or WSL.

## Configuration

To enable SSH access on a training job, set `session_provider` to `SSH` in your `config.py`:

```python config.py {17-20} theme={"system"}
from truss_train import TrainingProject, TrainingJob, Image, Compute, Runtime
from truss_train.definitions import (
    InteractiveSession,
    InteractiveSessionTrigger,
    InteractiveSessionProvider,
)
from truss.base.truss_config import AcceleratorSpec

training_job = TrainingJob(
    image=Image(base_image="pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime"),
    compute=Compute(
        accelerator=AcceleratorSpec(accelerator="H200", count=1),
    ),
    runtime=Runtime(
        start_commands=["python train.py"],
    ),
    interactive_session=InteractiveSession(
        trigger=InteractiveSessionTrigger.ON_STARTUP,
        session_provider=InteractiveSessionProvider.SSH,
    ),
)

training_project = TrainingProject(name="my-training-project", job=training_job)
```

This example sets `trigger=ON_STARTUP` so the session is available as soon as the job starts running. The default is `ON_DEMAND`, which activates the session on your first SSH connection; see [Trigger modes](/training/remote-access#trigger-modes) for all options.

Training jobs support H200 and H100 GPUs. For all `InteractiveSession` fields, see the [SDK reference](/reference/sdk/training#interactivesession). For supported compute, see [Compute resources](/training/concepts/basics#compute-resources).

## Quick start with CLI

To create an SSH-enabled workstation without writing a `config.py`, use the `truss train workstation` command. It configures an interactive session with `InteractiveSessionTrigger.ON_STARTUP` and runs `sleep infinity` to keep the container alive.

```bash theme={"system"}
# Default: 1x H100
uvx truss train workstation

# 4x H200 with custom project name
uvx truss train workstation --accelerator H200 --gpu-count 4 --project-id my-dev-box

# Custom base image
uvx truss train workstation --image pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime
```

Once the workstation is running, connect using the SSH command provided in the output. See the [CLI reference](/reference/cli/training/training-cli#workstation) for all available options.

For multi-node workstations, pass `--node-count` instead of `--gpu-count`: Baseten bootstraps a Slurm cluster across the nodes. See [Slurm workstations](/training/slurm).

## Quick start

This walkthrough uses the
[MNIST PyTorch example](https://github.com/basetenlabs/ml-cookbook/tree/main/examples/mnist-pytorch/training)
to push a training job with SSH enabled, then connects to the container from your terminal.

### Set up your machine

Run `uvx truss ssh setup` once to configure OpenSSH:

```bash theme={"system"}
uvx truss ssh setup
```

This generates an SSH keypair, installs a `ProxyCommand` helper, and adds a wildcard `Host` entry to `~/.ssh/config`. You only need to do this once per machine.

The expected output is:

```text theme={"system"}
SSH keypair: /Users/<you>/.ssh/baseten/id_ed25519
Proxy script: /Users/<you>/.ssh/baseten/proxy-command.py
SSH config updated: ~/.ssh/config
Default remote: <remote>

SSH access configured. Connect to a running workload with:

  Training job: ssh training-job-<job-id>-<node>.ssh.baseten.co
  Inference model: ssh model-<model-id>-<deployment-id>.ssh.baseten.co
```

Where:

* `/Users/<you>` is your local home directory.
* `<remote>` is your default remote from `~/.trussrc` (typically `baseten`).

If you've already run setup on this machine, the first line instead reads `WARNING: Existing SSH keypair found at <path>, reusing it.` You can safely ignore it.

### Clone the example

```bash theme={"system"}
git clone https://github.com/basetenlabs/ml-cookbook.git
cd ml-cookbook/examples/mnist-pytorch/training
```

### Configure and push the job

Edit `config.py` to add an `interactive_session` with `session_provider=SSH`, as shown in [Configuration](#configuration). Then push:

```bash theme={"system"}
uvx truss train push config.py
```

The expected output is:

```text theme={"system"}
✨ Training job successfully created!
🪵 View logs for your job via 'truss train logs --job-id <job_id> --tail'
🔍 View metrics for your job via 'truss train metrics --job-id <job_id>'
🌐 View job in the UI: https://app.baseten.co/training/<project_id>/logs/<job_id>
```

Where:

* `<job_id>` is your new training job's ID. Note it down; you'll use it to connect in the next step.
* `<project_id>` is the Baseten-assigned ID for the training project.

### Connect

Once the job is running, find its ID with `uvx truss train view`, then SSH in:

```bash theme={"system"}
ssh training-job-<job_id>-0.ssh.baseten.co
```

For example, to connect to node 0 of job `abc1234`:

```bash theme={"system"}
ssh training-job-abc1234-0.ssh.baseten.co
```

You're connected when you see a shell prompt like `root@baseten-training-job-<job_id>-multinode-0:~#`.

By default, your source files are extracted to `/b10/workspace` (available as `$BT_WORKING_DIR`). If you set [`enable_baseten_workdir=False`](/reference/sdk/training#param-enable-baseten-workdir), Baseten uses your base image's `WORKDIR` instead.

## How it works

When you run `ssh training-job-<job_id>-<node>.ssh.baseten.co`, the proxy helper reads your API key from `~/.trussrc`, calls Baseten's signing API to issue a short-lived SSH certificate, and routes the connection to the correct training job. Certificates refresh automatically on every connection, so you never need to manage keys or tokens manually.

## Hostname format

```text theme={"system"}
training-job-<job_id>-<node>.ssh.baseten.co
```

| Segment  | Description                                                                       | Example   |
| -------- | --------------------------------------------------------------------------------- | --------- |
| `job_id` | Training job ID. Find it with `uvx truss train view` or in the Baseten dashboard. | `abc1234` |
| `node`   | Node index, starting at 0.                                                        | `0`       |

Examples:

```bash theme={"system"}
# Single-node job
ssh training-job-abc1234-0.ssh.baseten.co

# Second node of a multi-node job
ssh training-job-xyz5678-1.ssh.baseten.co
```

## IDE integration

Because `uvx truss ssh setup` configures standard OpenSSH, tools that speak SSH can connect with the same hostname:

* **VS Code**: Install the [Remote - SSH](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh) extension, then connect to `training-job-<job_id>-<node>.ssh.baseten.co`.
* **Cursor**: Use the built-in SSH remote feature with `training-job-<job_id>-<node>.ssh.baseten.co`.

## Multi-node jobs

For [multi-node training jobs](/training/concepts/multinode), specify the node index in the hostname. Node 0 is the leader:

```bash theme={"system"}
# Leader node
ssh training-job-abc1234-0.ssh.baseten.co

# Worker node 1
ssh training-job-abc1234-1.ssh.baseten.co
```

## File transfer

Use `scp` or `sftp` with the same hostname to transfer files:

```bash theme={"system"}
# Copy a file to the training container
scp ./data.csv training-job-abc1234-0.ssh.baseten.co:/workspace/data.csv

# Copy results from the container
scp training-job-abc1234-0.ssh.baseten.co:/workspace/results.json ./results.json

# Interactive file browser
sftp training-job-abc1234-0.ssh.baseten.co
```

## Multiple remotes

If you only have one remote configured in `~/.trussrc`, you can skip this section. Baseten uses it automatically.

If you have multiple remotes, include the remote name in the hostname so the proxy script knows which credentials to use:

```text theme={"system"}
training-job-<job_id>-<node>.<remote>.ssh.baseten.co
```

For example, to connect using the `baseten-dev` remote:

```bash theme={"system"}
ssh training-job-abc1234-0.baseten-dev.ssh.baseten.co
```

## Session management

For how to view session status, change triggers, and extend session expiry, see the [Remote access overview](/training/remote-access#session-management).

## Troubleshooting

### "Invalid job id: must be a valid hash id"

Check that the job ID in the hostname is correct. Find your job ID with `uvx truss train view` or in the Baseten dashboard.

### "SSH keypair not found" or "command not found"

Run `uvx truss ssh setup` to configure your machine.

### "No api\_key for remote"

Truss 0.17.2 and later store your API key in your operating system's keyring after `truss login`, but the SSH proxy reads it from `~/.trussrc`. Log in with the keyring disabled so the key stays in `~/.trussrc`:

```bash Terminal theme={"system"}
BASETEN_TRUSS_AUTH_KEYRING_DISABLED=1 uvx truss login
```

### Connection refused or job unreachable

SSH requires the training job to be in the `RUNNING` state. Check with:

```bash theme={"system"}
uvx truss train view --job-id <job_id>
```

If the job is running but SSH still fails, the job may not have SSH enabled. Confirm `session_provider=InteractiveSessionProvider.SSH` is set in your [Configuration](#configuration).

### TLS errors

The proxy script requires Python 3.10 or newer. If you see TLS errors, re-run setup with a newer Python interpreter:

```bash theme={"system"}
uvx truss ssh setup --python $(which python3.12)
```
