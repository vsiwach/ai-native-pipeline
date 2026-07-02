# baseten model deployment replica
Source: https://docs.baseten.co/reference/cli/baseten/model-deployment-replica

Manage replicas of a deployment

## terminate

```sh theme={"system"}
baseten model deployment replica terminate [OPTIONS]
```

Terminate a single replica of a model deployment.

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
  ID of the replica.
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

Terminate a replica without the confirmation prompt

```sh theme={"system"}
baseten model deployment replica terminate --model-id <model-id> --deployment-id <deployment-id> --replica-id <replica-id> --yes
```

### Filter output with `--jq`

Print just the success flag

```sh theme={"system"}
baseten model deployment replica terminate --model-id <model-id> --deployment-id <deployment-id> --replica-id <replica-id> --yes --jq '.success'
```

### Output

**Text mode (`--output text`):** On success, prints "Terminated replica `id` of deployment `id`" to stderr; no stdout output.

**JSON mode (`--output json`):** payload type `managementapi.TerminateReplicaResponse`.
