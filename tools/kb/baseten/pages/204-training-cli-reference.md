# Training CLI reference
Source: https://docs.baseten.co/reference/cli/training/training-cli

Deploy, manage, and monitor training jobs using the Truss CLI.

The `truss train` command provides subcommands for managing the full training job lifecycle.

```sh theme={"system"}
truss train [COMMAND] [OPTIONS]
```

***

## init

Initialize a training project from templates or create an empty project.

```sh theme={"system"}
truss train init [OPTIONS]
```

### Options

<ParamField>
  List all available examples.
</ParamField>

<ParamField type="TEXT" />

<ParamField type="TEXT" />

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Customizes logging.
</ParamField>

<ParamField>
  Disables interactive prompts, use in CI / automated execution contexts.
</ParamField>

### Examples

Initialize a project from a template:

```sh theme={"system"}
truss train init --examples qwen3-8b-lora-dpo-trl
```

Initialize multiple templates:

```sh theme={"system"}
truss train init --examples qwen3-8b-lora-dpo-trl,qwen3-8b-lora-verl
```

List available templates:

```sh theme={"system"}
truss train init --list-examples
```

Create an empty training project:

```sh theme={"system"}
truss train init
```

***

## push

Submit and run a training job.

```sh theme={"system"}
truss train push [OPTIONS] CONFIG
```

### Arguments

<ParamField type="string">
  Path to the training configuration file (for example, `config.py`).
</ParamField>

### Options

<ParamField type="TEXT">
  Remote to use.
</ParamField>

<ParamField>
  Tail for status + logs after push.
</ParamField>

<ParamField type="TEXT">
  Name of the training job.
</ParamField>

<ParamField type="TEXT">
  Team name for the training project

  <Note>
    The `--team` flag is only available if your organization has teams enabled. [Contact us](mailto:support@baseten.co) to enable teams, or see [Teams](/organization/teams) for more information.
  </Note>
</ParamField>

<ParamField type="on_startup | on_failure | on_demand">
  Interactive session trigger mode
</ParamField>

<ParamField type="INTEGER">
  Interactive session timeout in minutes
</ParamField>

<ParamField type="TEXT">
  Accelerator type and count (e.g., H200:8)
</ParamField>

<ParamField type="INTEGER">
  Number of compute nodes
</ParamField>

<ParamField type="TEXT">
  Entrypoint command.
</ParamField>

<ParamField type="INTEGER">
  Job priority (higher values run first when capacity frees up).
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Customizes logging.
</ParamField>

<ParamField>
  Disables interactive prompts, use in CI / automated execution contexts.
</ParamField>

### Examples

Submit a training job:

```sh theme={"system"}
truss train push config.py
```

Submit and stream logs:

```sh theme={"system"}
truss train push config.py --tail
```

Submit to a specific team:

```sh theme={"system"}
truss train push config.py --team my-team-name
```

Submit with a custom job name:

```sh theme={"system"}
truss train push config.py --job-name fine-tune-v1
```

***

## logs

Fetch and stream logs from a training job.

```sh theme={"system"}
truss train logs [OPTIONS]
```

### Options

<ParamField type="TEXT">
  Remote to use.
</ParamField>

<ParamField type="TEXT">
  Project ID.
</ParamField>

<ParamField type="TEXT">
  Project name or project id.
</ParamField>

<ParamField type="TEXT">
  Job ID.
</ParamField>

<ParamField>
  Tail for ongoing logs.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Customizes logging.
</ParamField>

<ParamField>
  Disables interactive prompts, use in CI / automated execution contexts.
</ParamField>

### Examples

Stream logs for a specific job:

```sh theme={"system"}
truss train logs --job-id abc123 --tail
```

View logs for a job without streaming:

```sh theme={"system"}
truss train logs --job-id abc123
```

***

## metrics

View real-time metrics for a training job including CPU, GPU, and storage usage.

```sh theme={"system"}
truss train metrics [OPTIONS]
```

### Options

<ParamField type="TEXT">
  Project ID.
</ParamField>

<ParamField type="TEXT">
  Project name or project id.
</ParamField>

<ParamField type="TEXT">
  Job ID.
</ParamField>

<ParamField type="TEXT">
  Remote to use.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Customizes logging.
</ParamField>

<ParamField>
  Disables interactive prompts, use in CI / automated execution contexts.
</ParamField>

### Examples

View metrics for a specific job:

```sh theme={"system"}
truss train metrics --job-id abc123
```

***

## view

List training projects and jobs, or view details for a specific job. This command lists jobs in the `TRAINING_JOB_PENDING` state (waiting for GPU capacity) alongside other active jobs.

```sh theme={"system"}
truss train view [OPTIONS]
```

### Options

<ParamField type="TEXT">
  View training jobs for a project.
</ParamField>

<ParamField type="TEXT">
  Project name or project id.
</ParamField>

<ParamField type="TEXT">
  View a specific training job.
</ParamField>

<ParamField type="TEXT">
  Remote to use.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Customizes logging.
</ParamField>

<ParamField>
  Disables interactive prompts, use in CI / automated execution contexts.
</ParamField>

### Examples

List all training projects:

```sh theme={"system"}
truss train view
```

View jobs in a specific project:

```sh theme={"system"}
truss train view --project my-project
```

View details for a specific job:

```sh theme={"system"}
truss train view --job-id abc123
```

***

## stop

Stop a running or pending training job.

```sh theme={"system"}
truss train stop [OPTIONS]
```

### Options

<ParamField type="TEXT">
  Project ID.
</ParamField>

<ParamField type="TEXT">
  Project name or project id.
</ParamField>

<ParamField type="TEXT">
  Job ID.
</ParamField>

<ParamField>
  Stop all running jobs.
</ParamField>

<ParamField type="TEXT">
  Remote to use.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Customizes logging.
</ParamField>

<ParamField>
  Disables interactive prompts, use in CI / automated execution contexts.
</ParamField>

### Examples

Stop a specific job:

```sh theme={"system"}
truss train stop --job-id abc123
```

Stop all running jobs:

```sh theme={"system"}
truss train stop --all
```

***

## recreate

Recreate an existing training job with the same configuration.

```sh theme={"system"}
truss train recreate [OPTIONS]
```

### Options

<ParamField type="TEXT">
  Job ID of Training Job to recreate
</ParamField>

<ParamField type="TEXT">
  Remote to use.
</ParamField>

<ParamField>
  Tail for status + logs after recreation.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Customizes logging.
</ParamField>

<ParamField>
  Disables interactive prompts, use in CI / automated execution contexts.
</ParamField>

### Examples

Recreate a specific job:

```sh theme={"system"}
truss train recreate --job-id abc123
```

Recreate and stream logs:

```sh theme={"system"}
truss train recreate --job-id abc123 --tail
```

***

## download

Download training job artifacts to your local machine.

```sh theme={"system"}
truss train download [OPTIONS]
```

### Options

<ParamField type="TEXT">
  Job ID.
</ParamField>

<ParamField type="TEXT">
  Remote to use.
</ParamField>

<ParamField type="DIRECTORY">
  Directory where the file should be downloaded. Defaults to current directory.
</ParamField>

<ParamField>
  Instructs truss to not unzip the folder upon download.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Customizes logging.
</ParamField>

<ParamField>
  Disables interactive prompts, use in CI / automated execution contexts.
</ParamField>

### Examples

Download artifacts to current directory:

```sh theme={"system"}
truss train download --job-id abc123
```

Download to a specific directory:

```sh theme={"system"}
truss train download --job-id abc123 --target-directory ./downloads
```

Download without extracting:

```sh theme={"system"}
truss train download --job-id abc123 --no-unzip
```

***

## deploy\_checkpoints

Deploy a trained model checkpoint to Baseten's inference platform.

```sh theme={"system"}
truss train deploy_checkpoints [OPTIONS]
```

### Options

<ParamField type="TEXT">
  Project ID.
</ParamField>

<ParamField type="TEXT">
  Project name or project id.
</ParamField>

<ParamField type="TEXT">
  Job ID.
</ParamField>

<ParamField type="TEXT">
  path to a python file that defines a DeployCheckpointsConfig
</ParamField>

<ParamField>
  Generate a truss config without deploying
</ParamField>

<ParamField type="TEXT">
  Path to output the truss config to. If not provided, will output to truss\_configs/`model_version_name`*`model_version_id` or truss\_configs/dry\_run*`timestamp` if dry run.
</ParamField>

<ParamField type="TEXT">
  Remote to use.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Customizes logging.
</ParamField>

<ParamField>
  Disables interactive prompts, use in CI / automated execution contexts.
</ParamField>

### Examples

Deploy checkpoints interactively:

```sh theme={"system"}
truss train deploy_checkpoints
```

Deploy checkpoints from a specific job:

```sh theme={"system"}
truss train deploy_checkpoints --job-id abc123
```

Preview deployment without deploying:

```sh theme={"system"}
truss train deploy_checkpoints --job-id abc123 --dry-run
```

### Output

After a successful deployment, the command prints a labeled block with the Model ID, Deployment ID, and a link to the deployment's logs page.

***

## get\_checkpoint\_urls

Get presigned URLs for checkpoint artifacts.

```sh theme={"system"}
truss train get_checkpoint_urls [OPTIONS]
```

### Options

<ParamField type="TEXT">
  Job ID.
</ParamField>

<ParamField type="TEXT">
  Remote to use.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Customizes logging.
</ParamField>

<ParamField>
  Disables interactive prompts, use in CI / automated execution contexts.
</ParamField>

### Examples

Get checkpoint URLs for a job:

```sh theme={"system"}
truss train get_checkpoint_urls --job-id abc123
```

***

## checkpoints list

List and interactively explore checkpoints for a training job.

```sh theme={"system"}
truss train checkpoints list [OPTIONS]
```

### Options

<ParamField type="TEXT">
  Remote to use.
</ParamField>

<ParamField type="TEXT">
  Project ID.
</ParamField>

<ParamField type="TEXT">
  Project name or project id.
</ParamField>

<ParamField type="TEXT">
  Job ID.
</ParamField>

<ParamField type="TEXT">
  Jump directly into a specific checkpoint's files.
</ParamField>

<ParamField type="checkpoint-id | size | created | type">
  Sort checkpoints by checkpoint-id, size, created date, or type.
</ParamField>

<ParamField type="asc | desc">
  Sort order: ascending or descending.
</ParamField>

<ParamField type="cli-table | csv | json">
  Output format: cli-table (default), csv, or json.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Customizes logging.
</ParamField>

<ParamField>
  Disables interactive prompts, use in CI / automated execution contexts.
</ParamField>

### Interactive mode

When using the default `cli-table` format in an interactive terminal, the command launches a checkpoint explorer:

1. **Checkpoint picker**: fuzzy-search and select a checkpoint from the list.
2. **File explorer**: navigate the checkpoint's directory tree. Press `→` or `Enter` to open a directory or view a file. Press `←` to go back. Press `Ctrl-C` to quit.

For `.safetensors` files, the explorer displays a tensor summary (layer names, dtypes, shapes, and parameter counts) instead of raw binary content. Text files display with syntax highlighting based on their file extension (for example, `.json`, `.py`, `.yaml`, `.toml`), falling back to plain text for unrecognized types.

### Examples

List checkpoints for the most recent job:

```sh theme={"system"}
truss train checkpoints list
```

List checkpoints for a specific job:

```sh theme={"system"}
truss train checkpoints list --job-id abc123
```

Jump directly into a checkpoint's files:

```sh theme={"system"}
truss train checkpoints list --job-id abc123 --checkpoint-name ckpt-001
```

Export checkpoint list as JSON:

```sh theme={"system"}
truss train checkpoints list --job-id abc123 --output-format json
```

Sort by size descending:

```sh theme={"system"}
truss train checkpoints list --job-id abc123 --sort size --order desc
```

***

## cache summarize

View a summary of the training cache for a project.

```sh theme={"system"}
truss train cache summarize [OPTIONS] PROJECT
```

### Arguments

<ParamField type="string">
  Project name or project ID.
</ParamField>

### Options

<ParamField type="TEXT">
  Remote to use.
</ParamField>

<ParamField type="filepath | size | modified | type | permissions">
  Sort files by filepath, size, modified date, file type, or permissions.
</ParamField>

<ParamField type="asc | desc">
  Sort order: ascending or descending.
</ParamField>

<ParamField type="cli-table | csv | json">
  Output format: cli-table (default), csv, or json.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Customizes logging.
</ParamField>

<ParamField>
  Disables interactive prompts, use in CI / automated execution contexts.
</ParamField>

### Examples

View cache summary:

```sh theme={"system"}
truss train cache summarize my-project
```

Sort by size descending:

```sh theme={"system"}
truss train cache summarize my-project --sort size --order desc
```

Export as JSON:

```sh theme={"system"}
truss train cache summarize my-project --output-format json
```

***

## isession

View or update interactive session details for a training job, including auth codes and connection status.

```sh theme={"system"}
truss train isession [OPTIONS]
```

### Options

<ParamField type="TEXT">
  Job ID of the training job.
</ParamField>

<ParamField type="TEXT">
  Remote to use.
</ParamField>

<ParamField type="INTEGER">
  Minutes to extend the session timeout by
</ParamField>

<ParamField type="on_startup | on_failure | on_demand">
  Change the session trigger (cannot be changed on on\_startup sessions)
</ParamField>

<ParamField type="table | json">
  Output format (default: table)
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Customizes logging.
</ParamField>

<ParamField>
  Disables interactive prompts, use in CI / automated execution contexts.
</ParamField>

### Examples

View session details for a job:

```sh theme={"system"}
truss train isession --job-id abc123
```

Extend session timeout:

```sh theme={"system"}
truss train isession --job-id abc123 --update-timeout 60
```

Output as JSON:

```sh theme={"system"}
truss train isession --job-id abc123 --format json
```

***

## update\_session

Update the interactive session configuration on a running training job. At least one of `--trigger` or `--timeout-minutes` must be provided.

```sh theme={"system"}
truss train update_session [OPTIONS] JOB_ID
```

### Arguments

<ParamField type="string">
  Job ID of the training job to update.
</ParamField>

### Options

<ParamField type="on_startup | on_failure | on_demand">
  When to create the interactive session: 'on\_startup' creates on job start, 'on\_failure' creates on job failure, 'on\_demand' allows manual session creation.
</ParamField>

<ParamField type="INTEGER">
  Number of minutes before the interactive session times out.
</ParamField>

<ParamField type="TEXT">
  Remote to use.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Customizes logging.
</ParamField>

<ParamField>
  Disables interactive prompts, use in CI / automated execution contexts.
</ParamField>

### Examples

Change the session trigger:

```sh theme={"system"}
truss train update_session abc123 --trigger on_startup
```

Update the session timeout:

```sh theme={"system"}
truss train update_session abc123 --timeout-minutes 120
```

<Warning>
  `truss train update_session` requires API support that may not be available in all environments.
  If you receive a 404 error, set the trigger mode at push time using `--interactive on_startup` or `--interactive on_failure` instead.
</Warning>

***

## workstation

Spin up an SSH workstation on Baseten training infrastructure.

```sh theme={"system"}
truss train workstation [OPTIONS]
```

### Options

<ParamField type="T4 | L4 | A10G | V100 | A100 | A100_40GB | H100 | H200 | H100_40GB | B200 | L40S | RTX_PRO_6000 | B300">
  GPU type for the workstation (default: H100).
</ParamField>

<ParamField type="INTEGER RANGE">
  Number of GPUs for a single-node workstation (1-8, default: 1). Mutually exclusive with `--node-count`.
</ParamField>

<ParamField type="TEXT">
  Name of the training project that owns the workstation. Defaults to `workstation-\{accelerator}`, for example `workstation-H100`.
</ParamField>

<ParamField type="INTEGER RANGE">
  Number of full nodes to provision, each using all of its GPUs. Values above 1 bootstrap a Slurm cluster across the nodes. Mutually exclusive with `--gpu-count`.

  <Note>
    See [Slurm workstations](/training/slurm) for the cluster topology, verification steps, and how to launch distributed work.
  </Note>
</ParamField>

<ParamField type="slurm">
  Orchestrator bootstrapped across multi-node workstations. `slurm` is the only supported value. Ignored for single-node workstations.
</ParamField>

<ParamField type="TEXT">
  Docker base image for every node (default: `nvidia/cuda:12.8.1-devel-ubuntu24.04`). Multi-node workstations install Slurm with `apt` at startup, so use a Debian-based image.
</ParamField>

<ParamField>
  Mount checkpoint storage on the workstation. See [Checkpoints](/training/concepts/checkpoints).
</ParamField>

<ParamField type="TEXT">
  Path inside the container to save checkpoints.
</ParamField>

<ParamField type="INTEGER">
  Checkpoint volume size in GiB.
</ParamField>

<ParamField type="TEXT">
  Job ID to load the latest checkpoint from.
</ParamField>

<ParamField type="TEXT">
  Name of the remote in `.trussrc` to use.
</ParamField>

<ParamField>
  Stream workstation status and logs after launch.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Customizes logging.
</ParamField>

<ParamField>
  Disables interactive prompts, use in CI / automated execution contexts.
</ParamField>

### Examples

Launch a workstation with default settings:

```sh theme={"system"}
truss train workstation
```

Launch a multi-GPU workstation:

```sh theme={"system"}
truss train workstation --accelerator H200 --gpu-count 4
```

Launch a workstation with a custom base image:

```sh theme={"system"}
truss train workstation --image pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime
```

***

## capacity

Show GPU capacity limits and current usage for the organization.

```sh theme={"system"}
truss train capacity [OPTIONS]
```

### Options

<ParamField type="TEXT">
  Name of the remote to use
</ParamField>

### Examples

View capacity for the default remote:

```sh theme={"system"}
truss train capacity
```

***

## Ignore files and folders

Create a `.truss_ignore` file in your project root to exclude files from upload. Uses `.gitignore` syntax.

```plaintext .truss_ignore theme={"system"}
# Python cache files
__pycache__/
*.pyc
*.pyo
*.pyd

# Type checking
.mypy_cache/

# Testing
.pytest_cache/

# Large data files
data/
*.bin
```
