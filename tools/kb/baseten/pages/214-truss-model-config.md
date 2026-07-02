# truss model-config
Source: https://docs.baseten.co/reference/cli/truss/model-config

Fetch the config of a deployed model.

```sh theme={"system"}
truss model-config [OPTIONS]
```

Fetches the `config.yaml` of a deployed model from Baseten and prints it to stdout. Use this to inspect the exact configuration a deployment is running, or to recover a config when the original source is unavailable.

By default, the command prints the original `config.yaml` that was uploaded with the deployment. If no original is stored, it prints the parsed config rendered as YAML. Pass `--output json` to get the full structured response.

### Options

<ParamField type="TEXT">
  Name of the remote in `.trussrc`. If omitted, Truss prompts to select one.
</ParamField>

<ParamField type="TEXT">
  ID of the model.
</ParamField>

<ParamField type="TEXT">
  ID of the deployment.
</ParamField>

<ParamField type="text | json">
  Output format. `text` (default) prints the original `config.yaml` (or the parsed config rendered as YAML if no original is stored). `json` emits the full response (`config`, `raw_config`) as JSON to stdout.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Use in CI/automated contexts where stdin isn't a TTY.
</ParamField>

**Examples:**

Print the deployed config to stdout:

```sh theme={"system"}
truss model-config --model-id YOUR_MODEL_ID --deployment-id YOUR_DEPLOYMENT_ID
```

Save the deployed config to a file:

```sh theme={"system"}
truss model-config --model-id YOUR_MODEL_ID --deployment-id YOUR_DEPLOYMENT_ID > config.yaml
```

Get the full structured response as JSON:

```sh theme={"system"}
truss model-config --model-id YOUR_MODEL_ID --deployment-id YOUR_DEPLOYMENT_ID --output json
```

<Tip>
  To download the entire Truss directory (config plus model code), use [`truss download`](/reference/cli/truss/download) instead.
</Tip>
