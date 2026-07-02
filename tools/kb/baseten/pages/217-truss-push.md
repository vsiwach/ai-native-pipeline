# truss push
Source: https://docs.baseten.co/reference/cli/truss/push

Deploy a model to Baseten.

```sh theme={"system"}
truss push [OPTIONS] [TARGET_DIRECTORY]
```

Deploys a Truss to Baseten. By default, creates a published deployment.

<Note>
  Use the [REST model-creation flow](/examples/create-a-model-with-rest) to run the same archive-based push from a non-Python client (Go, JavaScript) or CI.
</Note>

### Options

<ParamField type="PATH">
  Path to a custom config file. Defaults to `config.yaml` in the Truss directory.
</ParamField>

<ParamField type="TEXT">
  Name of the remote in `.trussrc` to push to.

  <Note>
    In non-interactive mode (for example, in CI/CD), the command fails fast with a clear error if no remote is configured or if multiple remotes are available.
  </Note>
</ParamField>

<ParamField type="TEXT">
  Temporarily overrides the model name for this deployment without updating `config.yaml`.
</ParamField>

<ParamField>
  Published is now the default behavior for `truss push`. Previously required to create a published deployment. If no production deployment exists, the first published deployment is automatically promoted to production.
</ParamField>

<ParamField>
  Push as a published deployment and promote to production, even if a production deployment already exists.
</ParamField>

<ParamField type="TEXT">
  Push as a published deployment and promote into the specified environment. When specified, `--promote` is ignored.
</ParamField>

<ParamField>
  Preserve the previous production deployment's autoscaling settings. Can only be used with `--promote`.
</ParamField>

<ParamField>
  Disable downloading the Truss directory from the UI.
</ParamField>

<ParamField type="TEXT">
  Name of the deployment. Only applies to published deployments (not development deployments created with `--watch`). Must contain only alphanumeric, `.`, `-`, or `_` characters.
</ParamField>

<ParamField>
  Wait for deployment to complete before returning. Returns non-zero exit code if deploy or build fails.
</ParamField>

<ParamField type="INTEGER">
  Maximum time to wait for deployment status polling in seconds. Only applies when `--wait` is used. This is a client-side timeout for the polling loop. For a server-side deploy operation timeout, use `--deploy-timeout-minutes`.
</ParamField>

<ParamField>
  Attach git versioning info (sha, branch, tag) to the deployment. Can also be set permanently in `.trussrc`.
</ParamField>

<ParamField>
  Stream deployment logs after push.
</ParamField>

<ParamField>
  When pushing to an environment, preserve the instance type configured in the environment instead of using the resources from the Truss config. Default: `--preserve-env-instance-type`. Ignored if `--environment` is not specified.
</ParamField>

<ParamField type="INTEGER">
  Timeout in minutes for the deploy operation.
</ParamField>

<ParamField type="TEXT">
  Name of the team to deploy to. If not specified, Truss infers the team based on your team membership and existing models, or prompts for selection when ambiguous.

  <Note>
    The `--team` flag is only available if your organization has teams enabled. [Contact us](mailto:support@baseten.co) to enable teams, or see [Teams](/organization/teams) for more information.
  </Note>
</ParamField>

<ParamField type="TEXT">
  Pass a JSON string with key-value pairs. This will be attached to the deployment and can be used for searching and filtering.

  ```sh theme={"system"}
  truss push --labels '{"env": "staging", "team": "ml-platform", "version": "1.2.0"}'
  ```
</ParamField>

<ParamField>
  Create a development deployment, wait for it to deploy, then watch for source code changes and apply live patches. Use this for rapid iteration during development. Cannot be used with `--promote` or `--environment`.
</ParamField>

<ParamField>
  Apply model code changes by swapping the model class in-process without restarting the inference server. Preserves in-memory state like loaded weights and caches, but does not re-run `__init__()` or `load()`. If your changes add new instance state that `predict()` depends on, do a full reload instead. Requires `--watch`. When re-attaching to an existing deployment with `truss watch`, use [`--hot-reload`](/reference/cli/truss/watch) instead.
</ParamField>

<ParamField>
  Force a full rebuild without using cached layers.
</ParamField>

<ParamField type="BOOLEAN">
  Keep the development model warm by preventing scale-to-zero while watching. Default is `true`. Requires `--watch`. To disable, pass `--watch-no-sleep=false`.
</ParamField>

<ParamField type="text | json">
  Output format. `json` emits structured JSON to stdout and all other output (progress, logs) to stderr. Default is `text`.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Use in CI/automated contexts where stdin isn't a TTY.
</ParamField>

<Note>
  In non-interactive contexts like CI/CD, pass `--team` when your account has multiple teams. Without it, `truss push` exits with a `UsageError` that lists the available team names.
</Note>

<Note>
  Each `truss push --wait` invocation polls `GET /v1/models/{model_id}/deployments/{deployment_id}` once per second until the deployment becomes active. Fanning out `--wait` from CI or a cron job multiplies that poll rate by the number of concurrent invocations.

  Past roughly 8 concurrent invocations, the combined poll rate trips per-organization rate limits or upstream WAF protections. The symptom is repeated `Network error, unable to reach Baseten. Retrying...` log lines or hung HTTP calls.

  For higher fan-out, drop `--wait` and poll deployment status yourself on a longer interval, or stagger the pushes.
</Note>

### Arguments

<ParamField type="TEXT">
  A Truss directory. Defaults to current directory.
</ParamField>

**Examples:**

Deploy a published deployment from the current directory:

```sh theme={"system"}
truss push
```

You should see:

```output theme={"system"}
✨ Model my-model was successfully pushed ✨

   Model ID:      abc1d2ef
   Deployment ID: xyz123
   Endpoint:      model-abc1d2ef.api.baseten.co
   Logs:          https://app.baseten.co/models/abc1d2ef/logs/xyz123
```

Create a development deployment and start watching for changes:

```sh theme={"system"}
truss push --watch
```

Deploy and promote to production:

```sh theme={"system"}
truss push --promote
```

Deploy to a specific environment:

```sh theme={"system"}
truss push --environment staging
```

Deploy with a custom deployment name:

```sh theme={"system"}
truss push --deployment-name my-model_v1.0
```

Deploy with a custom config file:

```sh theme={"system"}
truss push --config my-config.yaml
```

Deploy to a specific team:

```sh theme={"system"}
truss push --team my-team-name
```

Deploy with JSON output:

```sh theme={"system"}
truss push --output json
```

Returns:

```json theme={"system"}
{
  "model_id": "abc123",
  "model_version_id": "xyz789",
  "predict_url": "https://model-abc123.api.baseten.co/deployment/xyz789/predict",
  "logs_url": "https://app.baseten.co/models/abc123/logs/xyz789",
  "is_draft": false
}
```

View the bundled file manifest during a push:

```sh theme={"system"}
truss push --log DEBUG
```

The `DEBUG` log level prints each packed file and its size:

```text theme={"system"}
DEBUG  Packing 4 files (4.8 MB) for upload:
  model/accidental_weights.bin (4.8 MB)
  config.yaml (39 B)
  model/model.py (29 B)
  requirements.txt (5 B)
```
