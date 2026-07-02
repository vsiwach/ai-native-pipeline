# baseten org secret
Source: https://docs.baseten.co/reference/cli/baseten/org-secret

Manage secrets

## list

```sh theme={"system"}
baseten org secret list [OPTIONS]
```

List secrets (metadata only; values are never returned).

### Options

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Filter to a specific team by name or ID. Defaults to all teams the caller belongs to.
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

List secrets across all accessible teams

```sh theme={"system"}
baseten org secret list
```

List secrets in a specific team

```sh theme={"system"}
baseten org secret list --team <team>
```

### Filter output with `--jq`

Print just the secret names

```sh theme={"system"}
baseten org secret list --jq '.secrets[].name'
```

### Output

**Text mode (`--output text`):** Table with columns: NAME, TEAM, CREATED. When no secrets exist, prints "No secrets found." to stderr.

**JSON mode (`--output json`):** payload type `managementapi.Secrets`.

## set

```sh theme={"system"}
baseten org secret set [OPTIONS]
```

Create or update a secret. The value is read from stdin (or prompted interactively on a TTY). `--value` is supported but discouraged: it leaks the secret into shell history and `ps` output. Pass `--team` to target a specific team; without it the organization's default team is used.

### Options

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  Name of the secret.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Team name or ID the secret belongs to. Defaults to the organization's default team.
</ParamField>

<ParamField type="TEXT">
  Secret value. Discouraged: leaks into shell history and process list. Prefer stdin or prompt.
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Set a secret by piping its value through stdin

```sh theme={"system"}
echo $TOKEN | baseten org secret set --name <name>
```

Set a secret scoped to a specific team

```sh theme={"system"}
echo $TOKEN | baseten org secret set --name <name> --team <team>
```

### Filter output with `--jq`

Print the secret's team

```sh theme={"system"}
echo $TOKEN | baseten org secret set --name <name> --jq '.team_name'
```

### Output

**Text mode (`--output text`):** Prints "Set secret `name`" to stderr on success; no stdout output.

**JSON mode (`--output json`):** payload type `managementapi.Secret`.

## delete

```sh theme={"system"}
baseten org secret delete [OPTIONS]
```

Delete a secret by name.

### Options

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  Name of the secret to delete.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Team name or ID the secret belongs to. Defaults to the organization's default team.
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Delete a secret by name

```sh theme={"system"}
baseten org secret delete --name <name>
```

### Filter output with `--jq`

Print just the deleted secret name

```sh theme={"system"}
baseten org secret delete --name <name> --jq '.name'
```

### Output

**Text mode (`--output text`):** Prints "Deleted secret `name`" to stderr on success; no stdout output.

**JSON mode (`--output json`):** payload type `managementapi.SecretTombstone`.
