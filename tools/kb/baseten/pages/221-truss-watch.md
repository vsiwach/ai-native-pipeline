# truss watch
Source: https://docs.baseten.co/reference/cli/truss/watch

Live reload during development.

```sh theme={"system"}
truss watch [OPTIONS] [TARGET_DIRECTORY]
```

Watches for source code changes and applies live patches to a development deployment. This enables rapid iteration without redeploying.

<Tip>
  You can create a development deployment and start watching in one step with `truss push --watch`.
</Tip>

### Options

<ParamField type="PATH">
  Path to a custom config file. Defaults to `config.yaml` in the Truss directory.
</ParamField>

<ParamField type="TEXT">
  Name of the remote in `.trussrc` to patch changes to.
</ParamField>

<ParamField type="TEXT">
  Name of the team to deploy to. If not specified, Truss infers the team based on your team membership and existing models, or prompts for selection when ambiguous.

  <Note>
    The `--team` flag is only available if your organization has teams enabled. [Contact us](mailto:support@baseten.co) to enable teams, or see [Teams](/organization/teams) for more information.
  </Note>
</ParamField>

<ParamField type="BOOLEAN">
  Keep the development model warm by preventing scale-to-zero while watching. Default is `true`. Pass `--no-sleep=false` to disable.
</ParamField>

<ParamField>
  Apply model code changes by swapping the model class in-process without restarting the inference server. Preserves in-memory state like loaded weights and caches, but does not re-run `__init__()` or `load()`. If your changes add new instance state that `predict()` depends on, do a full reload instead. When creating a new deployment with `truss push --watch`, use [`--watch-hot-reload`](/reference/cli/truss/push) instead.
</ParamField>

<ParamField type="TEXT">
  Temporarily overrides the model name for this session without updating `config.yaml`.
</ParamField>

<ParamField>
  Stream deployment logs while watching.
</ParamField>

<ParamField type="humanfriendly | W | WARNING | I | INFO | D | DEBUG">
  Logging verbosity. `humanfriendly` (default) is pretty-printed; `INFO`, `DEBUG`, `WARNING` produce structured logs.
</ParamField>

<ParamField>
  Disable interactive prompts. Use in CI/automated contexts where stdin isn't a TTY.
</ParamField>

### Arguments

<ParamField type="TEXT">
  A Truss directory. Defaults to current directory.
</ParamField>

**Examples:**

Watch for changes in the current directory:

```sh theme={"system"}
truss watch
```

You should see:

```
   Model ID:      abc1d2ef
   Deployment ID: xyz123
   Endpoint:      model-abc1d2ef.api.baseten.co
   Logs:          https://app.baseten.co/models/abc1d2ef/logs/xyz123
👀 Watching for changes to truss at '/path/to/my-model'...
```

When you edit a file, Truss detects the change and applies a live patch to the running deployment.

Watch a specific Truss directory:

```sh theme={"system"}
truss watch /path/to/my-truss
```

Watch with a custom config file:

```sh theme={"system"}
truss watch --config my-config.yaml
```
