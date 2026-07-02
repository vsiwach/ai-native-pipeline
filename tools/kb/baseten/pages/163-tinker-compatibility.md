# Tinker compatibility
Source: https://docs.baseten.co/loops/tinker-compatibility

Most Tinker code runs on Loops with one install change, apart from paginated checkpoints, auth, and cluster routing.

Most Tinker code runs on Loops with one install change. The forward pass, backward pass, optimizer step, sampling, and all shared types carry over without modification. Three things behave differently: checkpoints come back as paginated presigned URLs rather than a single archive, authentication uses a `BASETEN_API_KEY` instead of a Thinking Machines key, and cluster routing resolves to your Baseten org rather than a Tinker tenant.

## Compatibility at a glance

The `baseten-loops[tinker]` extra installs a `tinker` namespace package so existing imports work unchanged. The table below shows where the two systems align and where they diverge.

| Aspect                         | Tinker                      | Loops                                                 |
| ------------------------------ | --------------------------- | ----------------------------------------------------- |
| Import                         | `import tinker`             | `import tinker` (provided by `baseten-loops[tinker]`) |
| ServiceClient construction     | `tinker.ServiceClient(...)` | `tinker.ServiceClient()`                              |
| Forward / backward / optimizer | identical                   | identical                                             |
| Checkpoint download            | single archive              | paginated presigned URLs                              |
| Authentication                 | Thinking Machines key       | `BASETEN_API_KEY`                                     |
| Cluster scope                  | per Tinker tenant           | per Baseten org                                       |

## Install the Tinker compatibility package

Add `baseten-loops` with the `[tinker]` extra to your project. The extra pulls in `baseten-loops-tinker`, which provides the `tinker` namespace. If you don't have a uv project yet, initialize one first:

```bash theme={"system"}
uv init loops-app
cd loops-app
uv add 'baseten-loops[tinker]'
```

Once installed, existing code that starts with `import tinker` works without modification:

```python theme={"system"}
import tinker  # provided by baseten-loops-tinker
```

### Use with tinker-cookbook

`tinker-cookbook` depends on the original Thinking Machines `tinker` package. Without an override, installing `tinker-cookbook` first pulls in that package, and its files conflict with the `tinker` namespace provided by `baseten-loops[tinker]` when that extra is added later. The fix is to declare a `uv` override in `pyproject.toml` before installing any dependencies. There is no CLI command for this step.

Add the override first:

```toml theme={"system"}
[tool.uv]
override-dependencies = [
    "tinker ; python_version < '0'",
]
```

Then add the dependencies:

```bash theme={"system"}
uv init
uv add tinker-cookbook
uv add 'baseten-loops[tinker]'
```

The `baseten-loops[tinker]` extra provides the `tinker` namespace instead of the original package.

## What's the same

The training loop API is identical between the two systems. `forward`, `backward`, `optim_step`, `save_weights`, and the sampling interface share the same method names and argument shapes. The shared types (`Datum`, `ModelInput`, `TensorData`, `SamplingParams`, and `AdamParams`) are all available under `tinker.types` with the same field names and semantics.

## What's different

### Checkpoints come back as folders

Tinker returns a single archive URL for a checkpoint. Loops returns a folder of files behind paginated presigned URLs, because weight sync writes an unzipped folder rather than a compressed archive. Consumer code paginates using `?page_token=` and `?page_size=` query parameters instead of downloading a single file. See [`GET /v1/loops/checkpoints/{checkpoint_id}/files`](/reference/loops-api/checkpoints/get-checkpoint-files) for the route.

### Authentication is a Baseten API key

Set `BASETEN_API_KEY` in your environment before constructing `ServiceClient`; the SDK reads it by default. Pass `api_key=...` only when you need to override the environment variable. The Thinking Machines key used by Tinker is not accepted. See [API keys](/organization/api-keys) for how to generate one.

### Cluster routing is per-org

Loops sessions resolve to the caller's Baseten org and the cluster configured for that org. Tinker uses per-tenant scoping, where the tenant determines the cluster. In practice this means you don't choose a cluster when creating a session. Your org's configuration determines it automatically. Loops must be enabled for your organization before sessions can start; [fill out the signup form](https://www.baseten.co/talk-to-us/loops-signup/) to request access.

## Run tinker-cookbook recipes on Loops

The cookbook recipes contain self-contained examples covering supervised fine-tuning, reinforcement learning from human feedback, distillation, and sampling. They run on Loops without modification to training logic. Running a recipe end to end is the fastest way to confirm that your environment is configured correctly and that the `tinker` namespace is resolving to the Loops compatibility package.
