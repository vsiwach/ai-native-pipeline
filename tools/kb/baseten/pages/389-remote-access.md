# Remote access
Source: https://docs.baseten.co/training/remote-access

Connect to running training jobs from your local machine to debug, inspect state, and develop interactively.

Baseten offers two ways to connect to a running training container: **SSH** for terminal sessions and file transfer, and **VS Code and Cursor remote tunnels** for IDE-based debugging.

| Method                                             | Best for                                                         | Requirements                                                                         |
| -------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| [SSH](/training/ssh)                               | Terminal sessions, file transfer with `scp` or `sftp`, scripting | OpenSSH client, `truss ssh setup` run once                                           |
| [VS Code & Cursor](/training/interactive-sessions) | Debugging and editing inside an IDE                              | VS Code or Cursor with the Remote - Tunnels extension, a Microsoft or GitHub account |

<Note>
  SSH sessions must be enabled for your Baseten workspace. [Contact support](mailto:support@baseten.co) to request access. Remote tunnel sessions are available to all workspaces.
</Note>

## Configuration at a glance

Configure both methods on the `InteractiveSession` field of your `TrainingJob`. Set `session_provider` to choose the connection method. These examples set `trigger=ON_STARTUP` so the session is available from job start; the default is `ON_DEMAND`, covered in [Trigger modes](#trigger-modes):

```python config.py theme={"system"}
from truss_train.definitions import (
    InteractiveSession,
    InteractiveSessionTrigger,
    InteractiveSessionProvider,
)

# SSH: connect from any OpenSSH client
interactive_session=InteractiveSession(
    trigger=InteractiveSessionTrigger.ON_STARTUP,
    session_provider=InteractiveSessionProvider.SSH,
)

# VS Code Remote Tunnels (default): connect from VS Code or Cursor
interactive_session=InteractiveSession(
    trigger=InteractiveSessionTrigger.ON_STARTUP,
    session_provider=InteractiveSessionProvider.VS_CODE,
)
```

For more information, see the [SDK reference](/reference/sdk/training#interactivesession) for all `InteractiveSession` fields.

## Trigger modes

The `trigger` field controls when the session's container stays alive for interactive use, and applies to both SSH and remote tunnel sessions.

| Mode         | When to use                                                                | Behavior                                                                                                                                                |
| ------------ | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `on_startup` | Develop interactively, run commands, or test code while training runs.     | Session is active from job start. Your `start_commands` still run alongside the session.                                                                |
| `on_failure` | Debug a failing training run. Your most common choice for production jobs. | Session activates when training exits with a non-zero exit code. The container stays alive for you to inspect the failure.                              |
| `on_demand`  | Decide later whether you need a session. This is the default.              | Session activates when you connect (SSH) or authenticate through the device code flow (remote tunnel), or when you change the trigger on a running job. |

### On-demand session activation

If you pushed a job with `on_demand` (the default), activate it in one of two ways:

* **SSH**: Connect with `ssh training-job-<job_id>-<node>.ssh.baseten.co`. The session activates on first connection.
* **Remote tunnel**: Complete the device code flow. Open the **Auth URL** and enter the **Auth Code** from `truss train isession`.

You can also activate a session by changing the trigger on a running job:

```bash theme={"system"}
truss train isession --job-id <job_id> --update-trigger on_startup
```

## Clone a private GitHub repository

Training jobs sometimes need code from a private GitHub repo: an internal library, a dataset loader, or the training script itself. The right flow depends on whether you're connecting interactively or running unattended.

### With SSH agent forwarding

Best for interactive work over SSH. Agent forwarding doesn't apply to [interactive sessions](/training/interactive-sessions), which connect through Remote Tunnels. Use the [PAT flow](#with-a-personal-access-token) for those.

Load your GitHub-registered key into the local agent, then connect with `-A`:

```bash theme={"system"}
ssh-add ~/.ssh/id_ed25519
ssh -A training-job-<job_id>-0.ssh.baseten.co
```

From inside the container, clone over SSH:

```bash theme={"system"}
git clone git@github.com:<org>/<repo>.git
```

The `~/.ssh/config` block written by `uvx truss ssh setup` doesn't include `ForwardAgent yes`. Pass `-A` on every connection, or append `ForwardAgent yes` to the `Match host training-job-*.ssh.baseten.co` block in `~/.ssh/config`.

The SSH agent forgets added keys on reboot. On macOS, add keys to your login keychain to reload them automatically:

```bash theme={"system"}
ssh-add --apple-use-keychain ~/.ssh/id_ed25519
```

Or set `AddKeysToAgent yes` and `UseKeychain yes` in `~/.ssh/config`. On Windows, the OpenSSH `ssh-agent` service keeps added keys across reboots.

### With a personal access token

Best when the repo needs to be pulled before you connect, for example from `start_commands`. Store a [fine-grained GitHub PAT](https://github.com/settings/personal-access-tokens) with **Contents: Read-only** as a [Baseten secret](/organization/secrets), then inject it through a [`SecretReference`](/reference/sdk/training#secretreference):

```python config.py theme={"system"}
from truss_train.definitions import SecretReference

runtime=Runtime(
    start_commands=[
        "git clone https://x-access-token:${GITHUB_PAT}@github.com/<org>/<repo>.git $BT_WORKING_DIR/repo",
    ],
    environment_variables={"GITHUB_PAT": SecretReference(name="github_pat")},
),
```

The `x-access-token` username is GitHub's convention for token-based HTTPS auth. `$GITHUB_PAT` stays set for the container's lifetime, so later `git pull` or `git fetch` commands reuse the same credential.

<Warning>
  Don't pass PATs as plain strings in `environment_variables`. Use `SecretReference` so the value doesn't land in source control.
</Warning>

## Session management

Both SSH and remote tunnel sessions share the same management commands.

### Session status

Check auth codes, connection status, and trigger:

```bash theme={"system"}
truss train isession --job-id <job_id>
```

For SSH sessions, the auth code columns are empty. SSH uses certificate-based auth instead of device codes.

### Live session logs

The `--tail` flag on `truss train logs` displays a live view with the session table pinned at the top and training logs streaming below:

```bash theme={"system"}
truss train logs --job-id <job_id> --tail
```

### Session timeout

Use `--update-timeout` to add minutes to the session expiry:

```bash theme={"system"}
truss train isession --job-id <job_id> --update-timeout 120
```

See the [CLI reference](/reference/cli/training/training-cli#isession) for all `isession` options.
