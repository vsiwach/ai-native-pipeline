# baseten org api-key
Source: https://docs.baseten.co/reference/cli/baseten/org-api-key

Manage API keys

## list

```sh theme={"system"}
baseten org api-key list [OPTIONS]
```

List API keys (metadata only; key values are never returned).

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

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

List all API keys in the org

```sh theme={"system"}
baseten org api-key list
```

### Filter output with `--jq`

Print just the prefixes of personal keys

```sh theme={"system"}
baseten org api-key list --jq '.keys[] | select(.type == "PERSONAL") | .prefix'
```

### Output

**Text mode (`--output text`):** Table with columns: NAME, KEY (prefix + \*\*\*\*), TYPE, TEAM. When no keys exist, prints "No API keys found." to stderr.

**JSON mode (`--output json`):** payload type `managementapi.APIKeys`.

## create

```sh theme={"system"}
baseten org api-key create [OPTIONS]
```

Create a new API key. The key value is printed to stdout exactly once and cannot be retrieved later; capture or pipe it on creation. `--model-id` may be repeated to scope the key to specific models and is only valid with `--type` workspace-export-metrics or `--type` workspace-invoke.

### Options

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT (repeatable)">
  Restrict the key to a specific model. May be repeated. Only valid with --type workspace-export-metrics or workspace-invoke.
</ParamField>

<ParamField type="TEXT">
  Optional human-readable name for the key.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="TEXT">
  Team name or ID to create the key in. Defaults to the organization's default team.
</ParamField>

<ParamField type="TEXT">
  API key category.

  One of: `personal`, `workspace-export-metrics`, `workspace-invoke`, `workspace-manage-all`
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Create a personal API key

```sh theme={"system"}
baseten org api-key create --type personal --name <label>
```

Create a workspace-invoke key scoped to specific models

```sh theme={"system"}
baseten org api-key create --type workspace-invoke --model-id <id-1> --model-id <id-2>
```

### Filter output with `--jq`

Print just the raw key value

```sh theme={"system"}
baseten org api-key create --type personal --jq '.api_key'
```

### Output

**Text mode (`--output text`):** Prints the raw API key value on stdout (one line). Also prints "Save this key now. It will not be shown again." to stderr.

**JSON mode (`--output json`):** payload type `managementapi.APIKey`.

## delete

```sh theme={"system"}
baseten org api-key delete [OPTIONS]
```

Delete an API key. Exactly one of `--name` or `--prefix` is required: `--name` matches the human-readable name, `--prefix` matches the leading characters shown in `org api-key list`.

### Options

<ParamField type="TEXT">
  Filter JSON output with a jq expression; implies --output json (or jsonl for streamed commands)
</ParamField>

<ParamField type="TEXT">
  Human-readable name of the API key to delete.

  Mutually exclusive with other flags in group `identifier`.
</ParamField>

<ParamField type="TEXT">
  Output format

  One of: `text`, `json`, `jsonl`, `none`
</ParamField>

<ParamField type="TEXT">
  Prefix of the API key to delete (as shown in list).

  Mutually exclusive with other flags in group `identifier`.
</ParamField>

<ParamField type="TEXT">
  Use a specific stored profile for this command, overriding BASETEN\_PROFILE and the current profile
</ParamField>

<ParamField type="BOOL">
  Enable verbose logging
</ParamField>

### Examples

Delete an API key by name

```sh theme={"system"}
baseten org api-key delete --name <label>
```

Delete by visible prefix

```sh theme={"system"}
baseten org api-key delete --prefix <prefix>
```

### Filter output with `--jq`

Print just the deleted key's prefix

```sh theme={"system"}
baseten org api-key delete --name <label> --jq '.prefix'
```

### Output

**Text mode (`--output text`):** Prints "Deleted API key `prefix`" to stderr on success; no stdout output.

**JSON mode (`--output json`):** payload type `managementapi.APIKeyTombstone`.
