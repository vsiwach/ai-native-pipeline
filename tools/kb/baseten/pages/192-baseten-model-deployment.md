# baseten model deployment
Source: https://docs.baseten.co/reference/cli/baseten/model-deployment

Manage deployments of a model

## activate

```sh theme={"system"}
baseten model deployment activate [OPTIONS]
```

Activate a model deployment.

### Options

<ParamField type="TEXT">
  ID of the deployment.
</ParamField>

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  ID of the model.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Name of the model. Use --team to disambiguate when the same name exists in multiple teams.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Team name or ID. Only valid with --model-name.
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Activate a deployment

```sh theme={"system"}
baseten model deployment activate --model-id <model-id> --deployment-id <deployment-id>
```

### Filter output with `--jq`

Print just the success flag

```sh theme={"system"}
baseten model deployment activate --model-id <model-id> --deployment-id <deployment-id> --jq '.success'
```

### Output

**Text mode (`--output text`):** On success, prints "Activated deployment `id`" to stderr; no stdout output.

**JSON mode (`--output json`):** payload type `managementapi.ActivateResponse`.

## config

```sh theme={"system"}
baseten model deployment config [OPTIONS]
```

Fetch the config of a deployed model.

By default prints the original config.yaml. Use `--output json` to emit the full response \{config, raw\_config} as JSON.

### Options

<ParamField type="TEXT">
  ID of the deployment.
</ParamField>

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  ID of the model.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Name of the model. Use --team to disambiguate when the same name exists in multiple teams.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Team name or ID. Only valid with --model-name.
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Print the deployment's config.yaml

```sh theme={"system"}
baseten model deployment config --model-id <model-id> --deployment-id <deployment-id>
```

### Filter output with `--jq`

Extract the parsed model\_name field

```sh theme={"system"}
baseten model deployment config --model-id <model-id> --deployment-id <deployment-id> --jq '.config.model_name'
```

### Output

**Text mode (`--output text`):** The original config.yaml text (preserving comments and ordering) when available, otherwise the parsed config marshaled as YAML.

**JSON mode (`--output json`):** payload type `managementapi.DeploymentConfigResponse`.

The full \{config, raw\_config} envelope. raw\_config is the original config.yaml text; config is the parsed shape.

## deactivate

```sh theme={"system"}
baseten model deployment deactivate [OPTIONS]
```

Deactivate a model deployment.

Prompts for yes/no confirmation. Pass `--yes` to skip the prompt. When stdin is not a terminal, `--yes` is required.

### Options

<ParamField type="TEXT">
  ID of the deployment.
</ParamField>

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  ID of the model.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Name of the model. Use --team to disambiguate when the same name exists in multiple teams.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Team name or ID. Only valid with --model-name.
</ParamField>

<ParamField type="BOOL">
  Skip the interactive confirmation prompt. Required when stdin is not a terminal.
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Deactivate a deployment without the confirmation prompt

```sh theme={"system"}
baseten model deployment deactivate --model-id <model-id> --deployment-id <deployment-id> --yes
```

### Filter output with `--jq`

Print just the success flag

```sh theme={"system"}
baseten model deployment deactivate --model-id <model-id> --deployment-id <deployment-id> --yes --jq '.success'
```

### Output

**Text mode (`--output text`):** On success, prints "Deactivated deployment `id`" to stderr; no stdout output.

**JSON mode (`--output json`):** payload type `managementapi.DeactivateResponse`.

## download

```sh theme={"system"}
baseten model deployment download [OPTIONS]
```

Download the Truss source for a model deployment as an uncompressed tar.

Exactly one of `--out-file` or `--out-dir` is required. `--out-file` writes the raw tar bytes; `--out-dir` extracts the tar into the directory. Use `--overwrite` to replace an existing file or write into a non-empty directory.

### Options

<ParamField type="TEXT">
  ID of the deployment.
</ParamField>

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  ID of the model.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Name of the model. Use --team to disambiguate when the same name exists in multiple teams.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Extract the Truss tar into this directory.

  Mutually exclusive with other flags in group `download-out`.
</ParamField>

<ParamField type="TEXT">
  Save the Truss as an uncompressed tar file at this path.

  Mutually exclusive with other flags in group `download-out`.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="BOOL">
  Allow overwriting an existing file or non-empty directory.
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Team name or ID. Only valid with --model-name.
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Save the Truss as a tar file

```sh theme={"system"}
baseten model deployment download --model-id <model-id> --deployment-id <deployment-id> --out-file truss.tar
```

Extract the Truss into a directory

```sh theme={"system"}
baseten model deployment download --model-id <model-id> --deployment-id <deployment-id> --out-dir ./truss
```

### Filter output with `--jq`

Print just the destination path

```sh theme={"system"}
baseten model deployment download --model-id <model-id> --deployment-id <deployment-id> --out-file truss.tar --jq '.out_file'
```

### Output

**Text mode (`--output text`):** Writes the Truss to disk; prints progress and the final destination path to stderr; no stdout output.

**JSON mode (`--output json`):** payload type `cmd.ModelDeploymentDownloadResult`.

On success, stdout is a JSON object with either out\_file or out\_dir set to the path written.

## promote

```sh theme={"system"}
baseten model deployment promote [OPTIONS]
```

Promote a model deployment to an environment.

Defaults to the production environment. Cleanup of the previous deployment is controlled by the target environment's promotion cleanup strategy.

Prompts for yes/no confirmation. Pass `--yes` to skip the prompt. When stdin is not a terminal, `--yes` is required.

### Options

<ParamField type="TEXT">
  ID of the deployment.
</ParamField>

<ParamField type="TEXT">
  Target environment name. Defaults to production.
</ParamField>

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  ID of the model.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Name of the model. Use --team to disambiguate when the same name exists in multiple teams.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="BOOL">
  Use this deployment's instance type instead of preserving the target environment's.
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Team name or ID. Only valid with --model-name.
</ParamField>

<ParamField type="BOOL">
  Skip the interactive confirmation prompt. Required when stdin is not a terminal.
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Promote a deployment to production without the confirmation prompt

```sh theme={"system"}
baseten model deployment promote --model-id <model-id> --deployment-id <deployment-id> --yes
```

Promote to a non-production environment using the deployment's own instance type

```sh theme={"system"}
baseten model deployment promote --model-id <model-id> --deployment-id <deployment-id> --environment staging --override-env-instance-type --yes
```

### Filter output with `--jq`

Print the promoted deployment's status

```sh theme={"system"}
baseten model deployment promote --model-id <model-id> --deployment-id <deployment-id> --yes --jq '.status'
```

### Output

**Text mode (`--output text`):** On success, prints "Promoted deployment `id` to environment `env`" to stderr; no stdout output.

**JSON mode (`--output json`):** payload type `managementapi.Deployment`.

Under `--output json`, the promoted deployment object.

## delete

```sh theme={"system"}
baseten model deployment delete [OPTIONS]
```

Delete a single model deployment.

Deployments associated with an environment (e.g. production, development) and the only deployment of a model cannot be deleted server-side.

Prompts for yes/no confirmation. Pass `--yes` to skip the prompt. When stdin is not a terminal, `--yes` is required.

### Options

<ParamField type="TEXT">
  ID of the deployment.
</ParamField>

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  ID of the model.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Name of the model. Use --team to disambiguate when the same name exists in multiple teams.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Team name or ID. Only valid with --model-name.
</ParamField>

<ParamField type="BOOL">
  Skip the interactive confirmation prompt. Required when stdin is not a terminal.
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Delete a deployment without the confirmation prompt

```sh theme={"system"}
baseten model deployment delete --model-id <model-id> --deployment-id <deployment-id> --yes
```

### Filter output with `--jq`

Print the deleted deployment's ID

```sh theme={"system"}
baseten model deployment delete --model-id <model-id> --deployment-id <deployment-id> --yes --jq '.id'
```

### Output

**Text mode (`--output text`):** On success, prints "Deleted deployment `id`" to stderr; no stdout output.

**JSON mode (`--output json`):** payload type `managementapi.DeploymentTombstone`.

## describe

```sh theme={"system"}
baseten model deployment describe [OPTIONS]
```

Describe a model deployment by ID.

### Options

<ParamField type="TEXT">
  ID of the deployment.
</ParamField>

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  ID of the model.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Name of the model. Use --team to disambiguate when the same name exists in multiple teams.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Team name or ID. Only valid with --model-name.
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Describe a deployment by ID

```sh theme={"system"}
baseten model deployment describe --model-id <model-id> --deployment-id <deployment-id>
```

### Filter output with `--jq`

Print just the deployment status

```sh theme={"system"}
baseten model deployment describe --model-id <model-id> --deployment-id <deployment-id> --jq '.status'
```

### Output

**Text mode (`--output text`):** Field-per-line summary: ID, Name, Model, Environment (optional), Status, Instance (optional), Replicas, Created.

**JSON mode (`--output json`):** payload type `managementapi.Deployment`.

## list

```sh theme={"system"}
baseten model deployment list [OPTIONS]
```

List all deployments of a model.

### Options

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  ID of the model.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Name of the model. Use --team to disambiguate when the same name exists in multiple teams.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Team name or ID. Only valid with --model-name.
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

List all deployments of a model

```sh theme={"system"}
baseten model deployment list --model-id <model-id>
```

### Filter output with `--jq`

Print just the deployment IDs

```sh theme={"system"}
baseten model deployment list --model-id <model-id> --jq '.deployments[].id'
```

### Output

**Text mode (`--output text`):** Table with columns: ID, NAME, ENVIRONMENT, STATUS, INSTANCE, REPLICAS, CREATED. When no deployments exist, prints "No deployments found." to stderr.

**JSON mode (`--output json`):** payload type `managementapi.Deployments`.

## logs

```sh theme={"system"}
baseten model deployment logs [OPTIONS]
```

Fetch logs for a model deployment.

By default returns logs from the server's default recent window. Use `--start`/`--end` or `--since` to scope the window (max 7 days). Use `--tail` to stream live logs until the deployment leaves a runnable state or you interrupt with Ctrl-C.

For machine-readable streaming, prefer `--output jsonl` over `--output json`.

For request-ID tracing, scope, and log export, see [Logs](/observability/logs).

### Options

<ParamField type="TEXT">
  ID of the deployment.
</ParamField>

<ParamField type="TEXT">
  End of the log time range. Accepts ISO 8601; values without a timezone designator are interpreted in the local timezone. If omitted, the server defaults the end to now. Window must be at most 7 days.
</ParamField>

<ParamField type="TEXT (repeatable)">
  Case-sensitive substring; lines containing it are dropped. May be repeated.
</ParamField>

<ParamField type="TEXT (repeatable)">
  Case-sensitive substring that must appear in the log message. May be repeated; all must match.
</ParamField>

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  Only return logs at or above this severity level.

  One of: `debug`, `info`, `warning`, `error`
</ParamField>

<ParamField type="TEXT">
  ID of the model.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Name of the model. Use --team to disambiguate when the same name exists in multiple teams.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Only return logs emitted by this replica (5-char short ID).
</ParamField>

<ParamField type="TEXT">
  Only return logs tagged with this inference request ID.
</ParamField>

<ParamField type="TEXT">
  RE2 regular expression matched against the log message. Prefer --includes and --excludes for plain substring matches.
</ParamField>

<ParamField type="TEXT">
  Shortcut for fetching logs from a relative time ago until now. Accepts a Go duration (e.g. '30m', '1h30m') or '`N`d' (e.g. '3d'). Maximum '7d'. Mutually exclusive with --start and --end.
</ParamField>

<ParamField type="TEXT">
  Start of the log time range. Accepts ISO 8601 (e.g. '2026-05-14', '2026-05-14T12:00:00', '2026-05-14T12:00:00Z'). Values without a timezone designator are interpreted in the local timezone. If omitted, the server defaults the start to 30 minutes before the end. Window must be at most 7 days.
</ParamField>

<ParamField type="BOOL">
  Stream new logs as they arrive until the deployment leaves a runnable state or you interrupt with Ctrl-C. Cannot be combined with the time-range or filter flags. For machine-readable streaming, prefer --output jsonl over --output json.
</ParamField>

<ParamField type="TEXT">
  Team name or ID. Only valid with --model-name.
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Print logs for a deployment over the last hour

```sh theme={"system"}
baseten model deployment logs --model-id <model-id> --deployment-id <deployment-id> --since 1h
```

Print logs for a fixed time range

```sh theme={"system"}
baseten model deployment logs --model-id <model-id> --deployment-id <deployment-id> --start 2026-05-14T00:00:00Z --end 2026-05-15T00:00:00Z
```

Tail live logs until the deployment leaves a runnable state

```sh theme={"system"}
baseten model deployment logs --model-id <model-id> --deployment-id <deployment-id> --tail
```

Filter to warnings and above that contain a term

```sh theme={"system"}
baseten model deployment logs --model-id <model-id> --deployment-id <deployment-id> --min-level warning --includes timeout
```

### Filter output with `--jq`

Stream just the log messages as a JSONL stream

```sh theme={"system"}
baseten model deployment logs --model-id <model-id> --deployment-id <deployment-id> --output jsonl --jq '.message'
```

### Output

**Text mode (`--output text`):** One line per log record: "\[YYYY-MM-DD HH:MM:SS]: (replica) message".

**JSON mode (`--output json`):** payload type `managementapi.Log`.

## metrics

```sh theme={"system"}
baseten model deployment metrics [OPTIONS]
```

Fetch metrics for a model deployment. Use `--mode current` for a snapshot, `--mode summary` to aggregate a window, or `--mode series` to plot values over time. Scope the window with `--since` or `--start`/`--end`, and select metrics with one or more `--metric` flags.

### Options

<ParamField type="TEXT">
  ID of the deployment.
</ParamField>

<ParamField type="TEXT">
  End of the metrics time range. Accepts ISO 8601; values without a timezone designator are interpreted in the local timezone. If omitted, the server defaults the end to now. Window must be at most 7 days.
</ParamField>

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT (repeatable)">
  Name of a metric to return; see [https://docs.baseten.co/observability/export-metrics/supported-metrics](https://docs.baseten.co/observability/export-metrics/supported-metrics) for the available names. May be repeated. When omitted, a default set is returned.
</ParamField>

<ParamField type="TEXT">
  Aggregation mode. 'current' returns an instantaneous snapshot at now; 'summary' aggregates the whole window into one value per metric; 'series' returns evenly-spaced points across the window. --start/--end/--since are only meaningful for summary and series.

  One of: `current`, `summary`, `series`
</ParamField>

<ParamField type="TEXT">
  ID of the model.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="TEXT">
  Name of the model. Use --team to disambiguate when the same name exists in multiple teams.

  Mutually exclusive with other flags in group `model-ref`.
</ParamField>

<ParamField type="BOOL">
  For --mode series, emit a per-step table instead of sparklines.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Shortcut for a window from a relative time ago until now. Accepts a Go duration (e.g. '30m', '1h30m') or '`N`d' (e.g. '3d'). Maximum '7d'. Mutually exclusive with --start and --end.
</ParamField>

<ParamField type="TEXT">
  Start of the metrics time range. Accepts ISO 8601 (e.g. '2026-05-14', '2026-05-14T12:00:00', '2026-05-14T12:00:00Z'). Values without a timezone designator are interpreted in the local timezone. If omitted, the server defaults the start to one hour before the end. Window must be at most 7 days.
</ParamField>

<ParamField type="TEXT">
  Team name or ID. Only valid with --model-name.
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Show a current snapshot of the default metrics

```sh theme={"system"}
baseten model deployment metrics --model-name <model-name> --deployment-id <deployment-id>
```

Summarize request volume and latency over the last hour

```sh theme={"system"}
baseten model deployment metrics --model-id <model-id> --deployment-id <deployment-id> --mode summary --since 1h --metric baseten_inference_requests_total --metric baseten_end_to_end_response_time_seconds
```

Plot a series over the last 6 hours

```sh theme={"system"}
baseten model deployment metrics --model-id <model-id> --deployment-id <deployment-id> --mode series --since 6h
```

### Filter output with `--jq`

Print the metric names returned

```sh theme={"system"}
baseten model deployment metrics --model-id <model-id> --deployment-id <deployment-id> --jq '.metric_descriptors[].name'
```

### Output

**Text mode (`--output text`):** For `current` and `summary`, a table with columns METRIC, one column per label dimension (for example QUANTILE, STAT), and VALUE; summary counter values show "total (rate/s)". For `series`, a sparkline per metric label set with its min-max range and end value, or a per-step table under `--no-chart`.

**JSON mode (`--output json`):** payload type `cmd.DeploymentMetricsResult`.
