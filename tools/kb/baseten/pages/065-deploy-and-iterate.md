# Deploy and iterate
Source: https://docs.baseten.co/development/model/deploy-and-iterate

Use development deployments with live patching for rapid iteration, then promote to production.

Development deployments let you iterate on your model without redeploying from scratch each time you make a change. When you save a file, Truss detects the change, calculates a patch, and applies it to the running deployment in seconds.

<Tip>
  If `truss push --watch` isn't a good fit, [SSH access](/inference/ssh) lets you connect to a running deployment with standard SSH. SSH works well for custom servers that watch doesn't patch and for longer-lived interactive sessions. Pair it with a non-zero `min_replicas` and a code-syncing tool to iterate on a live container.
</Tip>

## Start a development deployment

Create a development deployment and start watching for changes:

```sh Terminal theme={"system"}
truss push --watch
```

Truss creates a development deployment, waits for it to build, and begins watching your project directory for file changes. Once the deployment reaches the `LOADING_MODEL` stage, Truss enters watch mode early so you can start iterating while the model finishes loading.

```output theme={"system"}
   Model ID:      abc1d2ef
   Deployment ID: xyz123
   Endpoint:      model-abc1d2ef.api.baseten.co
   Logs:          https://app.baseten.co/models/abc1d2ef/logs/xyz123
👀 Watching for changes to truss...
```

To apply model code changes without restarting the inference server, add the `--watch-hot-reload` flag:

```sh Terminal theme={"system"}
truss push --watch --watch-hot-reload
```

See [What gets live-patched](#what-gets-live-patched) for details and caveats about hot reload.

## Re-attach to a development deployment

If you stop the watch session (Ctrl+C), re-attach to the existing development deployment with:

```sh Terminal theme={"system"}
truss watch
```

You should see:

```output theme={"system"}
   Model ID:      abc1d2ef
   Deployment ID: xyz123
   Endpoint:      model-abc1d2ef.api.baseten.co
   Logs:          https://app.baseten.co/models/abc1d2ef/logs/xyz123
🚰 Attempting to sync truss with remote
No changes observed, skipping patching.
👀 Watching for new changes.
```

`truss watch` syncs any changes made while disconnected, then resumes watching. It requires an existing development deployment. If you don't have one, use `truss push --watch` to create it.

To apply model code changes without restarting, add the `--hot-reload` flag:

```sh Terminal theme={"system"}
truss watch --hot-reload
```

## What gets live-patched

Truss monitors your project directory (respecting `.trussignore` patterns) and applies patches for the following changes without a full rebuild:

| Change type           | Examples                                                                                                       |
| --------------------- | -------------------------------------------------------------------------------------------------------------- |
| Model code            | Files in the `model/` directory: `model.py`, helper modules, utilities, and binary files (like `.so`, `.png`). |
| Bundled packages      | Files in the `packages/` directory, including binary files (like `.pyd`, `.so`).                               |
| Python requirements   | Adding, removing, or updating packages in `requirements` or a requirements file.                               |
| Environment variables | Adding, removing, or updating values in `environment_variables`.                                               |
| External data         | Adding or removing entries in `external_data`.                                                                 |
| Config values         | Most `config.yaml` changes (except those listed below).                                                        |

With the `--watch-hot-reload` or `--hot-reload` flags, Truss hot-reloads model code changes by swapping the model class in-process without restarting the inference server. This preserves in-memory state like loaded weights and caches. If a patch includes non-model changes (such as requirements or config), Truss falls back to a standard restart.

<Warning>
  Hot reload re-imports your module and updates `__class__` on the existing model instance. It does not re-run `__init__()` or `load()`. If you add new instance state in those methods that `predict()` depends on, `predict()` calls will fail to see it. When your changes involve new instance state, stop the watch session and do a full reload with `truss push --watch`.
</Warning>

## What requires a full redeploy

The patch system doesn't support some changes. When you make these changes, stop the watch session and run `truss push` (or `truss push --watch` to start a new development deployment):

| Change type                   | Why                                                     |
| ----------------------------- | ------------------------------------------------------- |
| `resources` (GPU type, count) | Requires a new instance.                                |
| `python_version`              | Requires a new base image.                              |
| `system_packages`             | Requires apt installation in the container.             |
| `live_reload`                 | Changes the deployment mode.                            |
| Data directory (`data/`)      | The patch system doesn't track file changes in `data/`. |

<Tip>
  If a patch fails, Truss prints an error and continues watching. Fix the issue in your source files and save again. For persistent failures, run `truss push --watch` to start fresh.
</Tip>

## Limitations

Development deployments optimize for iteration, not production traffic:

* **Single replica**: Fixed at 0 minimum, 1 maximum. No autoscaling beyond one replica.
* **No gRPC**: Trusses with gRPC transport require a published deployment.
* **No TRT-LLM engine builds**: TRT-LLM build flow requires a published deployment.

See [Development deployments](/deployment/autoscaling/overview#development-deployments) for the full autoscaling constraints.

## Deploy to production

When you're done iterating, deploy a published version:

```sh Terminal theme={"system"}
truss push
```

By default, `truss push` creates a published deployment with full autoscaling support. Published deployments can scale to multiple replicas and are suitable for production traffic.

To deploy and promote directly to the production environment:

```sh Terminal theme={"system"}
truss push --promote
```

<CardGroup>
  <Card title="CLI reference: truss push" icon="terminal" href="/reference/cli/truss/push">
    Full list of options for the push command.
  </Card>

  <Card title="CLI reference: truss watch" icon="eye" href="/reference/cli/truss/watch">
    Full list of options for the watch command.
  </Card>

  <Card title="Autoscaling" icon="arrows-up-down" href="/deployment/autoscaling/overview">
    Configure replicas, concurrency targets, and scale-to-zero for production.
  </Card>

  <Card title="Environments" icon="layer-group" href="/deployment/environments">
    Manage staging, production, and custom environments.
  </Card>
</CardGroup>
