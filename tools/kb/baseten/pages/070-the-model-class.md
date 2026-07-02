# The Model class
Source: https://docs.baseten.co/development/model/model-class

Write custom Python in model/model.py to control how your model loads, runs inference, and shapes responses.

The `Model` class in `model/model.py` is the imperative surface you reach for when `config.yaml` alone can't express your logic. It gives you a Python class with lifecycle methods (`__init__`, `load`, and `predict`) that control how your model initializes, loads weights, and handles each request. When you need custom preprocessing, postprocessing, response shaping, or want to run an architecture that Baseten's built-in engines don't support, you write that logic here.

## When to write a Model class

Most deployments don't need custom Python. If you're deploying a supported open-source model, the config-only approach in [Build your first model](/development/model/build-your-first-model) is faster. Write a custom `Model` class when you need to:

* Run a model architecture that Baseten's engines don't support.
* Add custom preprocessing or postprocessing around inference.
* Combine multiple models or libraries in a single endpoint.
* Control the HTTP response directly, including status codes and streaming.

You define this logic in a `model/model.py` file. The simplest project structure is:

```text theme={"system"}
model/
  model.py
config.yaml
```

## The class skeleton

`model.py` must contain a class with three methods:

```python model.py theme={"system"}
class Model:
    def __init__(self, **kwargs):
        pass

    def load(self):
        pass

    def predict(self, model_input):
        return model_input
```

* `__init__` runs when the class is created. Read configuration parameters and runtime information here.
* `load` runs once at startup, before any requests. Download model weights or load them onto a GPU here. Separating this from `__init__` keeps expensive operations out of the request path.
* `predict` runs on every API request. Process input, run inference, and return the response.

<Warning>
  `load` and `predict` don't run on the same thread, which matters for GPU workloads where state can be tied to the creating thread (such as CUDA contexts). With sync `predict` and the default `predict_concurrency` of 1, successive `predict` calls often reuse the same worker thread, but Baseten doesn't guarantee it.
</Warning>

### `__init__`

The `__init__` method initializes the `Model` class. Use it to read configuration parameters and runtime information.

The simplest signature accepts nothing:

```python model.py theme={"system"}
def __init__(self):
    pass
```

If you need more information, define `__init__` to accept these parameters:

```python model.py theme={"system"}
def __init__(self, config: dict, data_dir: str, secrets: dict, environment: dict):
    pass
```

* `config`: A dictionary containing the `config.yaml` for the model.
* `data_dir`: A string containing the path to the data directory for the model.
* `secrets`: A dictionary containing the secrets for the model. At runtime, these are populated with the actual values stored on Baseten.
* `environment`: A dictionary containing the environment for the model, if the model has been deployed to an environment. `None` otherwise.

Save these as attributes to use them elsewhere in your model:

```python model.py theme={"system"}
def __init__(self, config: dict, data_dir: str, secrets: dict, environment: dict):
    self._config = config
    self._data_dir = data_dir
    self._secrets = secrets
    self._environment = environment
```

You can also accept these through `**kwargs` and pull out only what you need:

```python model.py theme={"system"}
def __init__(self, **kwargs):
    self._data_dir = kwargs["data_dir"]
    self._secrets = kwargs.get("secrets")
```

### `load`

The `load` method initializes the model. This might include downloading model weights or loading them onto the GPU. Unlike the other methods, `load` accepts no parameters:

```python model.py theme={"system"}
def load(self):
    pass
```

After you deploy your model, the deployment isn't considered "Ready" until `load` completes successfully. There is a **timeout of 30 minutes** for this, after which the deployment is marked as failed if `load` hasn't completed.

### `predict`

The `predict` method runs inference. The simplest signature returns a value directly:

```python model.py theme={"system"}
def predict(self, model_input) -> str:
    return "Hello"
```

The return type of `predict` must be JSON-serializable, so it can be a `dict`, `list`, or `str`. See [Response objects](#response-objects) for stricter typing and direct control over the HTTP response.

#### Async vs. sync

The `predict` method is synchronous by default. If your inference depends on APIs that require `asyncio`, write `predict` as a coroutine:

```python model.py theme={"system"}
import asyncio

async def predict(self, model_input) -> dict:
    # Async logic here.
    await asyncio.sleep(1)
    return {"value": "Hello"}
```

<Warning>
  If you use `asyncio` in `predict`, do not perform blocking operations such as a synchronous file download. This can degrade performance.
</Warning>

#### Pre/post-processing

To separate I/O from inference and maximize throughput, define optional `preprocess` and `postprocess` methods alongside `predict`. Tasks like downloading images or formatting responses then run without blocking GPU or CPU execution:

```python model.py theme={"system"}
class Model:
    def __init__(self, **kwargs): ...
    def load(self): ...

    def preprocess(self, request):
        # Handle I/O before inference, such as downloading images.
        ...

    def predict(self, request):
        # Perform model inference.
        ...

    def postprocess(self, response):
        # Handle I/O after inference, such as formatting outputs.
        ...
```

<Tip>
  Pre/post-processing runs in separate threads and isn't subject to Truss's concurrency limits, so I/O-heavy tasks don't bottleneck compute resources.
</Tip>

Truss enforces concurrency limits on `predict` to prevent GPU or CPU overload:

```yaml config.yaml theme={"system"}
runtime:
  predict_concurrency: 5
```

If the model receives 10 requests with `predict_concurrency: 5`, all 10 start preprocessing concurrently, but only 5 run inference at a time. The rest wait until a slot frees up.

#### Streaming

Truss also supports streaming output incrementally instead of waiting for the full response. For the full pattern, see [Streaming output and endpoints](/development/model/streaming-and-endpoints).

## Response objects

By default, Truss wraps prediction results into an HTTP response. For advanced use cases, create response objects manually to:

* Control HTTP status codes.
* Use server-sent events (SSEs) for streaming responses.

To return a more strictly typed object than a `dict`, `list`, or `str`, return a Pydantic model:

```python model.py theme={"system"}
from pydantic import BaseModel

class Result(BaseModel):
    value: str

class Model:
    def predict(self, model_input) -> Result:
        return Result(value="Hello")
```

To control the raw HTTP response, return any subclass of `starlette.responses.Response`:

```python model.py theme={"system"}
import fastapi

class Model:
    def predict(self, inputs) -> fastapi.Response:
        return fastapi.Response(...)
```

For server-sent events, return a `StreamingResponse`. See [Streaming output and endpoints](/development/model/streaming-and-endpoints) for a complete SSE example.

<Tip>
  You can return a response from `predict` or `postprocess`, but not both. If `predict` returns a response or a generator, `postprocess` cannot be used.
</Tip>

<Warning>
  Response headers aren't fully propagated. Include any metadata in the response body.
</Warning>

<Info>
  To handle raw incoming requests, see [Using request objects](/development/model/streaming-and-endpoints#request-handling).
</Info>

## Bundled data

Most models need additional files at runtime, such as weights, tokenizers, configs, or reference datasets. For local files under \~1 GB total, bundle them in your Truss's `data/` directory. The contents are copied into your container image at build time and mounted at `/app/data` at runtime.

Access them from `model.py` through `kwargs["data_dir"]`:

```python model.py theme={"system"}
class Model:
    def __init__(self, **kwargs):
        self._data_dir = kwargs["data_dir"]

    def load(self):
        self.tokenizer = AutoTokenizer.from_pretrained(str(self._data_dir))
```

A bundled Truss might lay its `data/` directory out like this Stable Diffusion 2.1 example:

```text theme={"system"}
data/
    scheduler/
        scheduler_config.json
    text_encoder/
        config.json
        diffusion_pytorch_model.bin
    tokenizer/
        merges.txt
        tokenizer_config.json
        vocab.json
    unet/
        config.json
        diffusion_pytorch_model.bin
    vae/
        config.json
        diffusion_pytorch_model.bin
    model_index.json
```

<Warning>
  Use the `data/` directory only when it's under \~1 GB total. The files ship inside the container image, so every cold start re-pulls them, not just the first deploy. Larger bundles compound into slower scale-ups, and `truss push` itself slows down as the bundle grows.
</Warning>

For larger weights or remote sources (Hugging Face, S3, GCS, R2), use the [Baseten Delivery Network (BDN)](/development/model/bdn) instead. BDN mirrors weights once and serves them from caches close to your replicas, so cold starts read from local or nearby caches instead of pulling from the source on every scale-up.

### Download files at runtime

Use this pattern when you need fine-grained control over the download, such as decrypting files on the fly or lazily fetching a subset of a larger dataset. The example below loads weights from a private S3 bucket using `boto3`.

<Note>
  To load private S3 weights at deploy time, prefer [BDN with IAM credentials](/development/model/bdn#quick-start-with-iam-credentials). BDN mirrors the weights once and serves them from a multi-tier cache; the pattern below re-downloads on every cold start unless you add caching.
</Note>

Define AWS secrets in `config.yaml`:

```yaml config.yaml theme={"system"}
secrets:
  aws_access_key_id: null
  aws_secret_access_key: null
  aws_region: null # for example, us-east-1
  aws_bucket: null
```

<Warning>
  Do not store actual credentials in `config.yaml`. Add them securely to the [Baseten secrets manager](https://app.baseten.co/settings/secrets).
</Warning>

Authenticate with AWS in `model.py`, then deploy with `truss push --watch`:

```python model.py theme={"system"}
import boto3

class Model:
    def __init__(self, **kwargs):
        self._config = kwargs.get("config")
        secrets = kwargs.get("secrets")
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=secrets["aws_access_key_id"],
            aws_secret_access_key=secrets["aws_secret_access_key"],
            region_name=secrets["aws_region"],
        )
        self.s3_bucket = secrets["aws_bucket"]
```

<Tip>
  If your model downloads weights at runtime using custom code, [BDN proxy](/development/model/bdn#bdn-proxy) can cache those downloads across replicas. Available by request.
</Tip>

## Next steps

* [HTTP endpoints](/development/model/streaming-and-endpoints#v1-endpoints): Add `chat_completions`, `completions`, `embeddings`, `messages`, or `responses` to serve matching `/v1/*` routes.
* [Streaming output and endpoints](/development/model/streaming-and-endpoints): Return generated output incrementally.
* [Custom health checks](/development/model/health-checks): Define readiness and liveness behavior.
* [Configuration](/development/model/configuration): Full reference for `config.yaml` options.
* [Model weights](/development/model/bdn): Fetch large weights through BDN instead of bundling them, and cache runtime-written files with [runtime caching](/development/model/runtime-caching).
