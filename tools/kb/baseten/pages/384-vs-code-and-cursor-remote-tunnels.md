# VS Code and Cursor remote tunnels
Source: https://docs.baseten.co/training/interactive-sessions

Connect to training containers for remote debugging and development through VS Code or Cursor Remote Tunnels.

[VS Code Remote Tunnels](https://code.visualstudio.com/docs/remote/tunnels) and
their Cursor equivalent let your local IDE attach to a training container
without SSH keys, open ports, or direct network access. You authenticate through a
device code flow through Microsoft or GitHub, and the tunnel connects your IDE
to the container securely.

Use a remote tunnel to debug a failed training job, inspect state on a running
job, or develop interactively without resubmitting.

<Tip>
  If you prefer a standard terminal over an IDE, see [SSH access](/training/ssh) for direct SSH connections to training containers.
</Tip>

## Prerequisites

* **VS Code** or **Cursor** installed locally.
* The **[Remote - Tunnels](https://marketplace.visualstudio.com/items?itemName=ms-vscode.remote-server)** extension installed in your IDE.
* A **Microsoft** or **GitHub** account for device flow authentication.

## Quick start

This walkthrough uses the
[MNIST PyTorch example](https://github.com/basetenlabs/ml-cookbook/tree/main/examples/mnist-pytorch/training)
to push a training job with a remote tunnel enabled, then connects to the container.

### Clone the example

Clone the ml-cookbook and navigate to the MNIST training example:

```bash theme={"system"}
git clone https://github.com/basetenlabs/ml-cookbook.git
cd ml-cookbook/examples/mnist-pytorch/training
```

### Configure and push the job

Add an interactive session to your `config.py`:

```python config.py theme={"system"}
from truss_train import TrainingProject, TrainingJob, Image, Compute, Runtime
from truss_train.definitions import (
    InteractiveSession,
    InteractiveSessionTrigger,
    InteractiveSessionAuthProvider,
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
        auth_provider=InteractiveSessionAuthProvider.MICROSOFT, # You can also use GITHUB
    ),
)

training_project = TrainingProject(name="mnist-training", job=training_job)
```

Push the job:

```bash theme={"system"}
truss train push config.py
```

Once the job is running, retrieve the auth code using `truss train isession`:

```bash theme={"system"}
truss train isession --job-id <job_id>
```

The expected output will look similar to this:

```
Interactive Sessions for Job: <job_id>
Replica ID  Tunnel Name              Auth Code  Auth URL                             Generated At (Local)
r0          bt-session-<job_id>-0    AB12-CD34  https://login.microsoftonline.com/…  14:30:00 PST
```

<Tip>
  You can also view this table in `truss train logs --job-id <job_id> --tail` alongside your training logs.
</Tip>

### Authenticate and connect

Connecting to the tunnel relies on the
[Remote - Tunnels](https://marketplace.visualstudio.com/items?itemName=ms-vscode.remote-server)
extension in your IDE.

1. Open the **Auth URL** from the table in your browser.
2. Enter the **Auth Code** shown in the table.
3. Connect to the tunnel in your IDE:

<Tabs>
  <Tab title="VS Code">
    1) Open the command palette (`Cmd+Shift+P` on macOS, `Ctrl+Shift+P` on Windows/Linux).
    2) Select **Remote-Tunnels: Connect to Tunnel**.
    3) Select the tunnel named `bt-session-<job_id>-<node_rank>` (for example, `bt-session-abc123-0`).
  </Tab>

  <Tab title="Cursor">
    **One-time setup:**

    Cursor doesn't include the required tunnel extensions by default.
    You'll need to sideload them from VS Code.

    1. In **VS Code**, find the following extensions in the marketplace and download each as a VSIX file using the **Download VSIX** option on the extension page:
       * [Remote Explorer](https://marketplace.visualstudio.com/items?itemName=ms-vscode.remote-explorer) by Microsoft
       * [Remote - Tunnels](https://marketplace.visualstudio.com/items?itemName=ms-vscode.remote-server) by Microsoft
    2. In **Cursor**, open the command palette (`Cmd+Shift+P`) and select **Extensions: Install from VSIX...**. Install both VSIX files.
    3. Open the command palette and select **Remote Explorer: Focus on Remotes (Tunnels/SSH) View**.
    4. Click **Sign in to tunnels registered with Microsoft** and complete the authentication flow.

    **Connect to the tunnel:**

    1. Open the command palette (`Cmd+Shift+P`).
    2. Select **Remote-Tunnels: Connect to Tunnel**.
    3. Choose **Microsoft** when prompted.
    4. Select the tunnel named `bt-session-<job_id>-<node_rank>` (for example, `bt-session-abc123-0`).
  </Tab>
</Tabs>

Open your workspace to the desired folder path to start debugging, editing your training script, or running commands. By default, your source files are extracted to `/b10/workspace` (available as `$BT_WORKING_DIR`). If you set [`enable_baseten_workdir=False`](/reference/sdk/training#param-enable-baseten-workdir), Baseten uses your base image's `WORKDIR` instead.

## Trigger modes and session management

Trigger modes (`on_startup`, `on_failure`, `on_demand`), activating on-demand sessions, viewing status with `truss train isession`, and extending session timeouts are shared across SSH and remote tunnel sessions. For more information, see [Remote access](/training/remote-access#trigger-modes).

<Note>
  For remote tunnel sessions specifically: auth codes appear in `truss train isession` as soon as the tunnel starts, regardless of trigger mode. With `on_failure`, the container stays alive for interactive use only after training fails. With `on_demand`, the container stays alive only after you authenticate or explicitly change the trigger.
</Note>

## Configuration

Configure interactive sessions with CLI flags or the Python SDK.
CLI flags override SDK values when both are set.

<Tabs>
  <Tab title="CLI">
    Pass `--interactive` to [`truss train push`](/reference/cli/training/training-cli#push) with a [trigger mode](/training/remote-access#trigger-modes):

    ```bash theme={"system"}
    truss train push config.py \
      --interactive on_startup \
      --interactive-timeout-minutes 120
    ```

    Set `timeout_minutes` to `-1` to extend the session expiry to 10 years. See [Timeout and expiry](#timeout-and-expiry) for details.

    For SSH-enabled interactive workstations, use [`truss train workstation`](/reference/cli/training/training-cli#workstation).

    See the [CLI reference](/reference/cli/training/training-cli#push) for all `push` options.
  </Tab>

  <Tab title="Python SDK">
    Add an [`InteractiveSession`](/reference/sdk/training#interactivesession) to the `interactive_session` field on your [`TrainingJob`](/reference/sdk/training#trainingjob):

    ```python config.py theme={"system"}
    from truss_train import TrainingProject, TrainingJob, Image, Compute, Runtime
    from truss_train.definitions import (
        InteractiveSession,
        InteractiveSessionTrigger,
        InteractiveSessionAuthProvider,
        InteractiveSessionProvider,
    )
    from truss.base.truss_config import AcceleratorSpec

    training_job = TrainingJob(
        image=Image(base_image="pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime"),
        compute=Compute(
            accelerator=AcceleratorSpec(accelerator="H200", count=2),
        ),
        runtime=Runtime(
            start_commands=["chmod +x ./run.sh && ./run.sh"],
        ),
        interactive_session=InteractiveSession(
            trigger=InteractiveSessionTrigger.ON_FAILURE,
            timeout_minutes=480,
            auth_provider=InteractiveSessionAuthProvider.MICROSOFT, # You can also use GITHUB
            session_provider=InteractiveSessionProvider.VS_CODE, # You can also use CURSOR
        ),
    )

    training_project = TrainingProject(name="my-training-project", job=training_job)
    ```

    See the [SDK reference](/reference/sdk/training#interactivesession) for all `InteractiveSession` fields.
  </Tab>
</Tabs>

## Timeout and expiry

Sessions expire based on the `timeout_minutes` setting (default: 480 minutes, or 8 hours). Set `timeout_minutes` to `-1` to extend the expiry to 10 years.

1. When the tunnel starts successfully, Baseten sets the expiry to `now + timeout_minutes`.
2. Each time the tunnel reconnects, the expiry resets to `now + timeout_minutes`.
3. When the expiry passes, the session ends and the container shuts down.

<Note>
  The timeout resets on tunnel reconnection, not on general IDE activity.
  If you disconnect and reconnect, the timer resets.
  If you stay connected but idle, the session expires after the configured timeout.
</Note>

### What happens when a session expires

When a session expires, Baseten signals the container to shut down gracefully.
Baseten doesn't hard-kill the container. It receives the signal and exits cleanly.
Baseten preserves any files you saved to `$BT_CHECKPOINT_DIR`, but you lose unsaved work in the container's local filesystem.

## Multi-node sessions

For [multi-node training jobs](/training/concepts/multinode), Baseten creates one tunnel per node.
Each node gets its own auth code, and you connect to each node independently.

Tunnel names follow the format `bt-session-<job_id>-<node_rank>`, where `node_rank` starts at 0. For example, a 2-node job produces:

* `bt-session-abc123-0` (node 0)
* `bt-session-abc123-1` (node 1)

The `truss train isession` command displays auth codes for all nodes in a single table.
