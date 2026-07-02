# truss ssh
Source: https://docs.baseten.co/reference/cli/truss/ssh

SSH access to Baseten workloads.

```sh theme={"system"}
truss ssh [COMMAND] [OPTIONS]
```

Configures SSH access to Baseten workloads: training jobs and model replicas. For training usage, see [SSH access](/training/ssh). For models, enable [`runtime.remote_ssh`](/reference/truss-configuration#param-remote-ssh) in your Truss config.

## Subcommands

### setup

Configures OpenSSH on your machine to authenticate with Baseten and connect to workloads. Run this once per machine.

```sh theme={"system"}
truss ssh setup [OPTIONS]
```

Generates an SSH keypair, installs a `ProxyCommand` script, and adds a wildcard `Host` entry to `~/.ssh/config`. After running this once, connect to any running workload:

```sh theme={"system"}
# Training job, per node
ssh training-job-<job_id>-<node>.ssh.baseten.co

# Model deployment (requires runtime.remote_ssh.enabled in the Truss config)
ssh model-<model_id>-<deployment_id>.ssh.baseten.co

# Specific replica of a model deployment
ssh model-<model_id>-<deployment_id>-<replica_id>.ssh.baseten.co
```

#### Options

<ParamField type="TEXT">
  Path to a Python 3.10+ interpreter for the `ProxyCommand`. Auto-detected if omitted. Use this if you see TLS errors with the default Python.
</ParamField>

<ParamField type="TEXT">
  Default remote to use when the hostname doesn't specify one and `~/.trussrc` has multiple remotes. If you have a single remote, Baseten uses it automatically.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Use in CI/automated contexts where stdin isn't a TTY.
</ParamField>

#### Examples

Run one-time setup:

```sh theme={"system"}
truss ssh setup
```

If you see TLS errors, specify a newer Python:

```sh theme={"system"}
truss ssh setup --python /opt/homebrew/bin/python3.13
```

Set a default remote when multiple are configured:

```sh theme={"system"}
truss ssh setup --default-remote baseten-dev
```
