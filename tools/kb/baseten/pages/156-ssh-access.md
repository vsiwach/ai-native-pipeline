# SSH access
Source: https://docs.baseten.co/inference/ssh

Connect to running model deployments directly from your terminal with standard SSH.

SSH (Secure Shell) is a protocol for encrypted, authenticated access to a remote machine. With model deployments on Baseten, you can SSH into any running deployment and get a full terminal inside the model container to debug, inspect files, run commands, edit code, or transfer data with `scp` and `sftp`. This gives you the same control you'd have on a local box, running on Baseten-managed hardware.

## Prerequisites

<Note>
  Inference SSH must be enabled for your organization. [Contact support](mailto:support@baseten.co) to request access.
</Note>

* **Baseten account**: [Sign up](https://app.baseten.co/) and generate an [API key](https://app.baseten.co/settings/account/api_keys).
* **[uv](https://docs.astral.sh/uv/)**: This guide uses `uvx` to run [Truss](https://pypi.org/project/truss/) commands without a separate install step. Log in to Baseten:

  ```bash Terminal theme={"system"}
  uvx truss login
  ```
* **OpenSSH client**: Pre-installed on macOS and Linux. On Windows, use the OpenSSH optional feature or WSL.

## Configuration

To enable SSH access on a deployment, set [`runtime.remote_ssh.enabled`](/reference/truss-configuration#param-remote-ssh) to `true` in your `config.yaml`:

```yaml config.yaml {3-5} theme={"system"}
model_name: my-model

runtime:
  remote_ssh:
    enabled: true

resources:
  accelerator: H100
  use_gpu: true
```

Then push the model:

```bash Terminal theme={"system"}
uvx truss push
```

SSH access is available as soon as the deployment is `ACTIVE`. Re-deploying without this field disables SSH for the new deployment.

<Note>
  SSH requires the default container user (`app`, uid `60000`). Setting `docker_server.run_as_user_id` to a different value is incompatible with SSH and the push will fail validation.
</Note>

<Note>
  Active SSH sessions don't block scale-to-zero or scale-down. For longer interactive sessions, set a non-zero `min_replicas` so your replica isn't reclaimed mid-session.
</Note>

## Quick start

This walkthrough pushes a small model with SSH enabled, then connects to it from your terminal.

### Set up your machine

Run `uvx truss ssh setup` once to configure OpenSSH:

```bash Terminal theme={"system"}
uvx truss ssh setup
```

This generates an SSH keypair, installs a `ProxyCommand` helper, and adds wildcard `Host` entries to `~/.ssh/config`. You only need to do this once per machine.

The expected output is:

```text Output theme={"system"}
SSH keypair: /Users/<you>/.ssh/baseten/id_ed25519
Proxy script: /Users/<you>/.ssh/baseten/proxy-command.py
SSH config updated: ~/.ssh/config
Default remote: <remote>

SSH access configured. Connect to a running workload with:

  Training job: ssh training-job-<job-id>-<node>.ssh.baseten.co
  Inference model: ssh model-<model-id>-<deployment-id>.ssh.baseten.co
```

If you've already run setup on this machine, the first line instead reads `WARNING: Existing SSH keypair found at <path>, reusing it.` You can safely ignore it.

### Enable SSH and push

In your model's `config.yaml`, add the `runtime.remote_ssh` block shown in [Configuration](#configuration), then push:

```bash Terminal theme={"system"}
uvx truss push
```

The expected output ends with a deployment URL and IDs. Note both the **model ID** (8 characters) and the **deployment ID** (7 characters) as you'll use them to connect.

### Connect

Once the deployment is `ACTIVE`, SSH in with:

```bash Terminal theme={"system"}
ssh model-<model_id>-<deployment_id>.ssh.baseten.co
```

For example:

```bash Terminal theme={"system"}
ssh model-abc12345-def4567.ssh.baseten.co
```

You're connected when you see a shell prompt inside the model container. Your container runs as the non-root `app` user.

## How it works

When you run `ssh model-<model_id>-<deployment_id>.ssh.baseten.co`, the proxy helper reads your API key from `~/.trussrc`, calls Baseten's signing API to issue a short-lived SSH certificate scoped to that deployment, and routes the connection to a running replica's container. Certificates refresh automatically on every connection, so you never need to manage keys or tokens manually. Authorization uses your existing model permissions, so only users who can manage the model can SSH into it.

## Hostname format

```text Hostname theme={"system"}
model-<model_id>-<deployment_id>[-<replica_id>].ssh.baseten.co
```

| Segment         | Description                                                                                            | Example    |
| --------------- | ------------------------------------------------------------------------------------------------------ | ---------- |
| `model_id`      | Model ID (8 lowercase alphanumeric characters). Find it in the deployment URL or with the Baseten CLI. | `abc12345` |
| `deployment_id` | Deployment ID (7 lowercase alphanumeric characters). Each new push creates a new deployment.           | `def4567`  |
| `replica_id`    | Optional. Suffix that uniquely identifies one replica when the deployment has multiple.                | `xyz9a`    |

Examples:

```bash Terminal theme={"system"}
# Connect to any running replica of this deployment
ssh model-abc12345-def4567.ssh.baseten.co

# Connect to a specific replica by suffix
ssh model-abc12345-def4567-xyz9a.ssh.baseten.co
```

## IDE integration

Because `uvx truss ssh setup` configures standard OpenSSH, tools that speak SSH can connect with the same hostname:

* **VS Code**: Install the [Remote - SSH](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-ssh) extension, then connect to `model-<model_id>-<deployment_id>.ssh.baseten.co`.
* **Cursor**: Use the built-in SSH remote feature with `model-<model_id>-<deployment_id>.ssh.baseten.co`.

## Target a specific replica

Deployments with [autoscaling](/deployment/autoscaling/overview) can have many replicas. By default, Baseten routes your SSH session to one running replica. To pin to a specific replica (useful when reproducing a bug that only appears on one replica), append a unique replica-name suffix to the hostname:

```bash Terminal theme={"system"}
ssh model-abc12345-def4567-xyz9a.ssh.baseten.co
```

You can find replica names in the deployment's logs view in the Baseten dashboard or by listing pods through the platform's debug tools.

<Warning>
  Active SSH sessions don't protect a replica from being scaled down. If the autoscaler removes the replica you're connected to, your session is terminated along with it. Set a non-zero `min_replicas` to keep the replica from being reclaimed mid-session.
</Warning>

## File transfer

Use `scp` or `sftp` with the same hostname to transfer files:

```bash Terminal theme={"system"}
# Copy a file into the model container
scp ./data.json model-abc12345-def4567.ssh.baseten.co:/tmp/data.json

# Copy a file out of the container
scp model-abc12345-def4567.ssh.baseten.co:/tmp/output.json ./output.json

# Interactive file browser
sftp model-abc12345-def4567.ssh.baseten.co
```

## Multiple remotes

If you only have one remote configured in `~/.trussrc`, you can skip this section. Baseten uses it automatically.

If you have multiple remotes, include the remote name in the hostname so the proxy script knows which credentials to use:

```text Hostname theme={"system"}
model-<model_id>-<deployment_id>.<remote>.ssh.baseten.co
```

For example, to connect using the `baseten-dev` remote:

```bash Terminal theme={"system"}
ssh model-abc12345-def4567.baseten-dev.ssh.baseten.co
```

## Troubleshooting

### "SSH is not enabled for this deployment"

The deployment was pushed without `runtime.remote_ssh.enabled: true`. Add it to `config.yaml` and re-push to create a new deployment with SSH enabled. Existing deployments cannot be changed in place.

### "SSH keypair not found" or "command not found"

Run `uvx truss ssh setup` to configure your machine.

### "No api\_key for remote"

Truss 0.17.2 and later store your API key in your operating system's keyring after `truss login`, but the SSH proxy reads it from `~/.trussrc`. Log in with the keyring disabled so the key stays in `~/.trussrc`:

```bash Terminal theme={"system"}
BASETEN_TRUSS_AUTH_KEYRING_DISABLED=1 uvx truss login
```

### Connection refused or deployment unreachable

SSH requires the deployment to be in the `ACTIVE` state with at least one running replica. If the deployment is scaled to zero, send a request to wake it, or set a non-zero `min_replicas` while debugging. Confirm the deployment status in the Baseten dashboard.

### TLS errors

The proxy script requires Python 3.10 or newer. If you see TLS errors, re-run setup with a newer Python interpreter:

```bash Terminal theme={"system"}
uvx truss ssh setup --python $(which python3.12)
```
