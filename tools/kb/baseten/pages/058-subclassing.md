# Subclassing
Source: https://docs.baseten.co/development/chain/subclassing

Modularize and re-use Chainlet implementations

Sometimes you want to write one "main" implementation of a complicated inference
task, but then re-use it for similar variations. For example:

* Deploy it on different hardware and with different concurrency.
* Replace a dependency (for example, silence detection in audio files) with a
  different implementation of that step, while keeping all other processing
  the same.
* Deploy the same inference flow, but exchange the model weights used. For example, for
  a large and small version of an LLM or different model weights fine-tuned to
  domains.
* Add an adapter to convert between a different input/output schema.

In all of those cases, you can create lightweight subclasses of your main
chainlet.

These patterns can be combined with each other.

## Example base class

Define the base Chainlet and verify its behavior locally:

```python base_chainlet.py theme={"system"}
import asyncio
import truss_chains as chains


class Preprocess2x(chains.ChainletBase):
    async def run_remote(self, number: int) -> int:
        return 2 * number


class MyBaseChainlet(chains.ChainletBase):
    remote_config = chains.RemoteConfig(
        compute=chains.Compute(cpu_count=1, memory="100Mi"),
        options=chains.ChainletOptions(enable_b10_tracing=True),
    )

    def __init__(self, preprocess=chains.depends(Preprocess2x)):
        self._preprocess = preprocess

    async def run_remote(self, number: int) -> float:
        return 1.0 / await self._preprocess.run_remote(number)


# Assert base behavior.
with chains.run_local():
    chainlet = MyBaseChainlet()
    result = asyncio.run(chainlet.run_remote(4))
    assert result == 1 / (4 * 2)
```

## Adapter for different I/O

The base class `MyBaseChainlet` works with integer inputs and returns floats. If
you want to reuse the computation, but provide an alternative interface (for example,
for a different client with different request/response schema), you can create
a subclass which does the I/O conversion. The actual computation is delegated to
the base classes above:

```python string_io_adapter.py theme={"system"}
class ChainletStringIO(MyBaseChainlet):
    async def run_remote(self, number: str) -> str:
        return str(await super().run_remote(int(number)))


# Assert new behavior.
with chains.run_local():
    chainlet_string_io = ChainletStringIO()
    result = asyncio.run(chainlet_string_io.run_remote("4"))
    assert result == "0.125"
```

## Chain with substituted dependency

The base class `MyBaseChainlet` uses preprocessing that doubles the input. If
you want to use a different variant of preprocessing, while keeping
`MyBaseChainlet.run_remote` and everything else as is, you can define a shallow
subclass of `MyBaseChainlet` that uses a different dependency,
`Preprocess8x`, which multiplies by 8 instead of 2:

```python substituted_dependency.py theme={"system"}
class Preprocess8x(chains.ChainletBase):
    async def run_remote(self, number: int) -> int:
        return 8 * number


class Chainlet8xPreprocess(MyBaseChainlet):
    def __init__(self, preprocess=chains.depends(Preprocess8x)):
        super().__init__(preprocess=preprocess)


# Assert new behavior.
with chains.run_local():
    chainlet_8x_preprocess = Chainlet8xPreprocess()
    result = asyncio.run(chainlet_8x_preprocess.run_remote(4))
    assert result == 1 / (4 * 8)
```

## Override remote config

If you want to re-deploy a chain, but change some deployment options, for example, run
on different hardware, you can create a subclass and override `remote_config`:

```python override_config.py theme={"system"}
class Chainlet16Core(MyBaseChainlet):
    remote_config = chains.RemoteConfig(
        compute=chains.Compute(cpu_count=16, memory="100Mi"),
        options=chains.ChainletOptions(enable_b10_tracing=True),
    )

```

<Warning>
  Be aware that `remote_config` is a class variable. In the example above we
  created a completely new `RemoteConfig` value, because changing fields
  *inplace* would also affect the base class.

  If you want to share config between the base class and subclasses, you can
  define them in additional variables for example, for the image:

  ```python shared_config.py theme={"system"}
  DOCKER_IMAGE = chains.DockerImage(pip_requirements=[...], ...)


  class MyBaseChainlet(chains.ChainletBase):
      remote_config = chains.RemoteConfig(docker_image=DOCKER_IMAGE, ...)


  class Chainlet16Core(MyBaseChainlet):
      remote_config = chains.RemoteConfig(docker_image=DOCKER_IMAGE, ...)
  ```
</Warning>
