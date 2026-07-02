# Runtime caching
Source: https://docs.baseten.co/development/model/runtime-caching

Cache files your model writes at runtime so other replicas reuse them

b10cache stores files your model writes at runtime, such as `torch.compile` artifacts, so other replicas and deployments can reuse them. It's the supported path for runtime-written files that benefit from sharing. For read-only weights known at deploy time, use [BDN](/development/model/bdn) instead.

## How b10cache works

Deployments sometimes produce files that are useful to other replicas. Using `torch.compile`, for example, produces a cache that can speed up future `torch.compile` calls on the same function, reducing cold start time for other replicas.

b10cache stores these files. It's a volume mounted over the network onto each of your replicas, with two scopes:

### Organization scope: `/cache/org/`

Shared across every replica you deploy in your organization. Move a file into this directory and any replica can read it.

### Deployment scope: `/cache/model/`

Shared across every replica within a single deployment. Use this scope to keep deployment filesystems isolated.

<Danger>
  ### Not persistent object storage

  b10cache is reliable, but treat it as a cache, not a database. Always have a fallback path that runs if the file isn't there yet. For example, the first replica of a new deployment writes to b10cache rather than reading from it.
</Danger>

## Torch compile caching

PyTorch's `torch.compile` can cut inference time by up to 40%, but compiling the model adds latency to cold starts: it must compile before serving its first request.

This overhead compounds in production, where:

* Models scale up and down with demand.
* New replicas spawn to handle traffic spikes.
* Each new replica repeats the compilation from scratch.

Torch compile caching persists compilation artifacts across deployments and replica restarts in b10cache, so a new replica loads them instead of recompiling. The library handles large scale-ups, managing race conditions and staying fault-tolerant on the shared cache.

In practice, this strategy reduces compilation latencies to roughly 5 to 20 seconds, depending on the model.

### Implementation options

There are two different deployment patterns that benefit from torch compile caching:

* **Truss models**: a `model.py` that calls `torch.compile`. See [Truss models](#truss-models-model-py).
* **vLLM servers**: a vLLM custom server. See [vLLM servers](#vllm-servers-cli-tool).

### Truss models (`model.py`)

#### API reference

We expose two API calls that return an `OperationStatus` object to help you control program flow based on the result.

<Accordion title="load_compile_cache()">
  If you have previously saved compilation cache for this model, load it to speed up the compilation for the model on this replica.

  **Returns:**

  * `OperationStatus.SUCCESS` → successful load
  * `OperationStatus.SKIPPED` → if torch compilation artifacts already exist on the replica
  * `OperationStatus.ERROR` → general catch-all errors
  * `OperationStatus.DOES_NOT_EXIST` → if no cache file was found
</Accordion>

<Accordion title="save_compile_cache()">
  Save your model's torch compilation cache for future use. This should be called after running prompts to warm up your model and trigger compilation.

  **Returns:**

  * `OperationStatus.SUCCESS` → successful save
  * `OperationStatus.SKIPPED` → skipped because compile cache already exists in shared directory
  * `OperationStatus.ERROR` → general catch-all errors
</Accordion>

#### Implementation example

Here is an example of compile caching for Flux, an image generation model. Note how we save the result of `load_compile_cache` to inform on whether to `save_compile_cache`.

##### Update `config.yaml`

Under requirements, add `b10-transfer`:

```yaml config.yaml theme={"system"}
requirements:
  - b10-transfer
```

##### Update `model.py`

Import the library and use the two functions to speed up torch compilation time:

```python model.py theme={"system"}
from b10_transfer import load_compile_cache, save_compile_cache, OperationStatus

class Model:
    def load(self):
        self.pipe = FluxPipeline.from_pretrained(
            self.model_name, torch_dtype=torch.bfloat16, token=self.hf_access_token
        ).to("cuda")

        # Try to load compile cache
        cache_loaded: OperationStatus = load_compile_cache()

        if cache_loaded == OperationStatus.ERROR:
            logging.info("Run in eager mode, skipping torch compile")
        else:
            logging.info("Compiling the model for performance optimization")
            self.pipe.transformer = torch.compile(
                self.pipe.transformer, mode="max-autotune-no-cudagraphs", dynamic=False
            )

            self.pipe.vae.decode = torch.compile(
                self.pipe.vae.decode, mode="max-autotune-no-cudagraphs", dynamic=False
            )

            seed = random.randint(0, MAX_SEED)
            generator = torch.Generator().manual_seed(seed)
            start_time = time.time()
            # Warmup the model with dummy prompts, also triggering compilation
            self.pipe(
                prompt="dummy prompt",
                prompt_2=None,
                guidance_scale=0.0,
                max_sequence_length=256,
                num_inference_steps=4,
                width=1024,
                height=1024,
                output_type="pil",
                generator=generator
            )

            end_time = time.time()

            logging.info(
                f"Warmup completed in {(end_time - start_time)} seconds. "
                "This is expected to take a few minutes on the first run."
            )

            if cache_loaded != OperationStatus.SUCCESS:
                # Save compile cache for future runs
                outcome: OperationStatus = save_compile_cache()
```

<Note>
  See the [full example](https://github.com/basetenlabs/truss-examples/tree/main/flux/schnell).
</Note>

### vLLM servers (CLI tool)

Use this whenever you enable compile options with vLLM (compiling is the default on vLLM V1). The CLI tool runs automatically: it loads the compile cache if you've saved one before, and saves it otherwise.

Make two changes in `config.yaml`:

#### Add requirements

Under requirements, add `b10-transfer`:

```yaml config.yaml theme={"system"}
requirements:
  - b10-transfer
```

#### Update start command

Under start command, add `b10-compile-cache &` right before the `vllm serve` call:

```yaml config.yaml theme={"system"}
start_command: "... b10-compile-cache & vllm serve ..."
```

<Note>
  See the [full example](https://github.com/basetenlabs/truss-examples/tree/main/mistral/mistral-small-3.1).
</Note>

### Advanced configuration

<Accordion title="Parameter overrides">
  The torch compile caching library supports several environment variables for fine-tuning behavior in production environments:

  #### Cache directory configuration

  **`TORCHINDUCTOR_CACHE_DIR`** (optional)

  * **Default**: `/tmp/torchinductor_<username>`
  * **Description**: Directory where PyTorch stores compilation artifacts locally
  * **Allowed prefixes**: `/tmp/`, `/cache/`, `~/.cache`
  * **Usage**: Set this if you need to customize where torch compilation artifacts are stored on the local filesystem

  **`B10FS_CACHE_DIR`** (optional)

  * **Default**: Derived from b10cache mount point + `/compile_cache`
  * **Description**: Directory in b10cache where compilation artifacts are persisted across deployments
  * **Usage**: Typically doesn't need to be changed as it's automatically configured based on your b10cache setup

  **`LOCAL_WORK_DIR`** (optional)

  * **Default**: `/app`
  * **Description**: Local working directory for temporary operations
  * **Allowed prefixes**: `/app/`, `/tmp/`, `/cache/`

  #### Performance and resource limits

  **`MAX_CACHE_SIZE_MB`** (optional)

  * **Default**: `1024` (1GB)
  * **Cap**: Limited by `MAX_CACHE_SIZE_CAP_MB` for safety
  * **Description**: Maximum size of a single cache archive in megabytes
  * **Usage**: Increase for larger models with extensive compilation artifacts, decrease to save storage

  **`MAX_CONCURRENT_SAVES`** (optional)

  * **Default**: `50`
  * **Cap**: Limited by `MAX_CONCURRENT_SAVES_CAP` for safety
  * **Description**: Maximum number of concurrent save operations allowed
  * **Usage**: Tune based on your deployment's concurrency requirements and storage performance

  #### Cleanup and maintenance

  **`CLEANUP_LOCK_TIMEOUT_SECONDS`** (optional)

  * **Default**: `30`
  * **Cap**: Limited by `LOCK_TIMEOUT_CAP_SECONDS`
  * **Description**: Timeout for cleaning up stale lock files, to prevent deadlocks. They may occur when a replica holding the lock crashes.
  * **Usage**: Decrease if you're experiencing deadlocks in high-load scenarios

  **`CLEANUP_INCOMPLETE_TIMEOUT_SECONDS`** (optional)

  * **Default**: `60`
  * **Cap**: Limited by `INCOMPLETE_TIMEOUT_CAP_SECONDS`
  * **Description**: Timeout for cleaning up incomplete cache files
  * **Usage**: Increase for slower storage systems or larger cache files

  #### Example configuration

  ```yaml config.yaml theme={"system"}
  environment_variables:
    MAX_CACHE_SIZE_MB: "2048"
    MAX_CONCURRENT_SAVES: "25"
    CLEANUP_LOCK_TIMEOUT_SECONDS: "45"
  ```

  <Note>
    The defaults suit most workloads. Tune them if a model needs a larger cache archive or hits contention on concurrent saves.
  </Note>
</Accordion>

To understand implementation details, read the [PyTorch torch compile caching tutorial](https://docs.pytorch.org/tutorials/recipes/torch_compile_caching_tutorial.html).

## Next steps

<CardGroup>
  <Card title="BDN" icon="database" href="/development/model/bdn">
    Cache read-only weights known at deploy time
  </Card>

  <Card title="Performance optimization" icon="gauge-high" href="/development/model/performance-optimization">
    Reduce latency and cold starts across your deployment
  </Card>
</CardGroup>
