# baseten model environment
Source: https://docs.baseten.co/reference/cli/baseten/model-environment

Manage environments of a model

## activate

```sh theme={"system"}
baseten model environment activate [OPTIONS]
```

Activate the deployment associated with an environment.

### Options

<ParamField type="TEXT">
  Name of the environment (e.g. production).
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

Activate the deployment associated with an environment

```sh theme={"system"}
baseten model environment activate --model-id <model-id> --environment production
```

### Filter output with `--jq`

Print just the success flag

```sh theme={"system"}
baseten model environment activate --model-id <model-id> --environment production --jq '.success'
```

### Output

**Text mode (`--output text`):** On success, prints "Activated environment `name`" to stderr; no stdout output.

**JSON mode (`--output json`):** payload type `managementapi.ActivateResponse`.

## deactivate

```sh theme={"system"}
baseten model environment deactivate [OPTIONS]
```

Deactivate the deployment associated with an environment.

Prompts for yes/no confirmation. Pass `--yes` to skip the prompt. When stdin is not a terminal, `--yes` is required.

### Options

<ParamField type="TEXT">
  Name of the environment (e.g. production).
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

Deactivate an environment without the confirmation prompt

```sh theme={"system"}
baseten model environment deactivate --model-id <model-id> --environment production --yes
```

### Filter output with `--jq`

Print just the success flag

```sh theme={"system"}
baseten model environment deactivate --model-id <model-id> --environment production --yes --jq '.success'
```

### Output

**Text mode (`--output text`):** On success, prints "Deactivated environment `name`" to stderr; no stdout output.

**JSON mode (`--output json`):** payload type `managementapi.DeactivateResponse`.

## describe

```sh theme={"system"}
baseten model environment describe [OPTIONS]
```

Describe a model environment by name.

### Options

<ParamField type="TEXT">
  Name of the environment (e.g. production).
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

Describe the production environment of a model

```sh theme={"system"}
baseten model environment describe --model-id <model-id> --environment production
```

### Filter output with `--jq`

Print the current deployment ID

```sh theme={"system"}
baseten model environment describe --model-id <model-id> --environment production --jq '.current_deployment.id'
```

### Output

**Text mode (`--output text`):** Field-per-line summary: Name, Model, Current Deployment, Status, Candidate Deployment (optional), Created.

**JSON mode (`--output json`):** payload type `managementapi.Environment`.

## list

```sh theme={"system"}
baseten model environment list [OPTIONS]
```

List all environments of a model.

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

List all environments of a model

```sh theme={"system"}
baseten model environment list --model-id <model-id>
```

### Filter output with `--jq`

Print just the environment names

```sh theme={"system"}
baseten model environment list --model-id <model-id> --jq '.environments[].name'
```

### Output

**Text mode (`--output text`):** Table with columns: NAME, CURRENT DEPLOYMENT, STATUS. When no environments exist, prints "No environments found." to stderr.

**JSON mode (`--output json`):** payload type `managementapi.Environments`.
