# Cache
Source: https://docs.baseten.co/training/concepts/cache

Learn how to use the training cache to speed up your training iterations by persisting data between jobs.

The training cache enables you to persist data between training jobs. This can significantly improve iteration speed by skipping expensive downloads and data transformations.

## How to use the training cache

Set the cache configuration in your `Runtime`:

```python theme={"system"}
from truss_train import definitions

training_runtime = definitions.Runtime(
    # ... other configuration options
    cache_config=definitions.CacheConfig(enabled=True)
)
```

## Cache directory

By default, the cache will be mounted in two locations:

* `/root/.cache/user_artifacts`, which can be accessed through the [`$BT_PROJECT_CACHE_DIR`](/reference/sdk/training#baseten-provided-environment-variables) environment variable. This cache is shared by all jobs in a project.
* `/root/.cache/team_artifacts`, which can be accessed through the [`$BT_TEAM_CACHE_DIR`](/reference/sdk/training#baseten-provided-environment-variables) environment variable. This cache is shared by all jobs for a team.

## Cache scope

Each cache lives on a single GPU cluster, so a job reuses cached data only when it runs on the cluster where that data was cached. When you enable the cache, your project pins to the cluster where its first cache-enabled job ran. Later jobs reuse that cache only if the GPU type you request is available on that cluster.

By default (`cache_config.require_cache_affinity=true`), requesting a GPU type the pinned cluster doesn't offer fails the job instead of running without the cache. Set `require_cache_affinity=false` to run on another cluster, where the cache starts empty until a job re-seeds it.

For read-only weights and datasets, load them through the [Baseten Delivery Network (BDN)](/development/model/bdn), which mirrors data across clusters and skips re-seeding.

## Hugging Face cache mount

You can mount your cache to the Hugging Face cache directory by setting `HF_HOME` to one of the provided mount points plus `/huggingface`. For example, you can set `HF_HOME=$BT_PROJECT_CACHE_DIR/huggingface` to use the project cache directory.

However, there are considerable technical pitfalls when trying to read from the cache with multiple processes, as Hugging Face doesn't work well with distributed filesystems. To help enable this use case, ensure your dataset processors or process count is set to 1 to minimize the number of concurrent readers.

## Seed your data and models

For multi-gpu training, you should ensure that your data is seeded before running multi-process training jobs. You can do this by separating out a data loading script and a training script.
For a 400 GB HF Dataset, you can expect to save *nearly an hour* of compute time for each job - data download and preparation have been done already!

## Cache management

You can inspect the contents of the cache through CLI with `truss train cache summarize <project_name or project_id>`. This visibility into what's in the cache can help you verify your code is working as expected, and additionally manage files and artifacts you no longer need.

<Warning>
  When you delete a project, all data in the project's training cache (`$BT_PROJECT_CACHE_DIR`) is permanently deleted with no archival or recovery option. See [Management](/training/management) for details.
</Warning>
