# Concepts
Source: https://docs.baseten.co/development/chain/concepts

Glossary of Chains concepts and terminology

This glossary defines the core Chains concepts you'll work with: Chainlets, their remote configuration and initialization, the `run_remote()` interface, entrypoints, and typed I/O. Read it alongside the [getting started guide](/development/chain/getting-started) when you build your first Chain.

## Chainlet

A Chainlet is the basic building block of Chains. A Chainlet is a Python class
that specifies:

* A set of compute resources.
* A Python environment with software dependencies.
* A typed interface [`run_remote()`](/development/chain/concepts#run-remote-chaining-chainlets) for other Chainlets to call.

This is the simplest possible Chainlet. Only the
[`run_remote()`](/development/chain/concepts#run-remote-chaining-chainlets) method is
required, and we can layer in other concepts to create a more capable Chainlet.

```python theme={"system"}
import truss_chains as chains


class SayHello(chains.ChainletBase):

    async def run_remote(self, name: str) -> str:
        return f"Hello, {name}"
```

You can modularize your code by creating your own chainlet sub-classes,
refer to our [subclassing guide](/development/chain/subclassing).

### Remote configuration

Chainlets are meant for deployment as remote services. Each Chainlet specifies
its own requirements for compute hardware (CPU count, GPU type and count, etc)
and software dependencies (Python libraries or system packages). This
configuration is built into a Docker image automatically as part of the
deployment process.

When no configuration is provided, the Chainlet will be deployed on a basic
instance with one vCPU, 2GB of RAM, no GPU, and a standard set of Python and
system packages.

Configuration is set using the
[`remote_config`](/reference/sdk/chains#remote-configuration) class variable
within the Chainlet:

```python theme={"system"}
import truss_chains as chains


class MyChainlet(chains.ChainletBase):
    remote_config = chains.RemoteConfig(
        docker_image=chains.DockerImage(
            pip_requirements=["torch==2.3.0", ...]
        ),
        compute=chains.Compute(gpu="H100", ...),
        assets=chains.Assets(secret_keys=["hf_access_token"], ...),
    )
```

To select an exact instance type instead of specifying individual resource fields, use `instance_type`:

```python theme={"system"}
compute=chains.Compute(instance_type="H100:8x80")
```

When `instance_type` is specified, `cpu_count`, `memory`, and `gpu` fields are ignored.

See the
[remote configuration reference](/reference/sdk/chains#remote-configuration)
for a complete list of options.

### Build commands

Use `build_commands` to run shell commands during the Docker image build, after system packages are installed and before your Chainlet code is added. Useful for cloning repositories, pre-downloading model weights, or other setup work you want cached at build time so it does not run on every cold start.

```python theme={"system"}
import truss_chains as chains


class ComfyChainlet(chains.ChainletBase):
    remote_config = chains.RemoteConfig(
        compute=chains.Compute(gpu="A100"),
        build_commands=[
            "git clone https://github.com/comfyanonymous/ComfyUI.git",
            "cd ComfyUI && pip install -r requirements.txt",
        ],
    )
```

Each entry runs as a separate shell command in the order listed. This is the Chains equivalent of the Truss [`build_commands`](/development/model/dependencies#build-commands) field in `config.yaml`.

### Initialization

Chainlets are implemented as classes because we often want to set up expensive
static resources once at startup and then re-use it with each invocation of the
Chainlet. For example, we only want to initialize an AI model and download its
weights once then re-use it every time we run inference.

We do this setup in `__init__()`, which is run exactly once when the Chainlet is
deployed or scaled up.

```python theme={"system"}
import truss_chains as chains


class PhiLLM(chains.ChainletBase):
    def __init__(self) -> None:
        import torch
        import transformers

        self._model = transformers.AutoModelForCausalLM.from_pretrained(
            PHI_HF_MODEL,
            torch_dtype=torch.float16,
            device_map="auto",
        )

        self._tokenizer = transformers.AutoTokenizer.from_pretrained(
            PHI_HF_MODEL,
        )
```

Chainlet initialization also has two important features: context and dependency
injection of other Chainlets, explained below.

#### Context (access information)

You can add a
[`DeploymentContext`](/reference/sdk/chains#class-truss_chains-deploymentcontext)
object as an optional argument to the `__init__`-method of a Chainlet.
This allows you to use secrets within your Chainlet, such as using
a `hf_access_token` to access a gated model on Hugging Face (note that when
using secrets, they also need to be added to the `assets`).

```python theme={"system"}
import truss_chains as chains


class MistralLLM(chains.ChainletBase):
    remote_config = chains.RemoteConfig(
        ...
    assets = chains.Assets(secret_keys=["hf_access_token"], ...),
    )

    def __init__(
        self,
        # Adding the `context` argument, allows us to access secrets
        context: chains.DeploymentContext = chains.depends_context(),
    ) -> None:
        import transformers

        # Using the secret from context to access a gated model on HF
        self._model = transformers.AutoModelForCausalLM.from_pretrained(
            "mistralai/Mistral-7B-Instruct-v0.2",
            use_auth_token=context.secrets["hf_access_token"],
        )
```

#### Depends (call other Chainlets)

The Chains framework uses the
[`chains.depends()`](/reference/sdk/chains#function-truss_chains-depends) function in
Chainlets' `__init__()` method to track the dependency relationship between
different Chainlets within a Chain.

This syntax, inspired by dependency injection, is used to translate local Python
function calls into calls to the remote Chainlets in production.

Once a dependency Chainlet is added with
[`chains.depends()`](/reference/sdk/chains#function-truss_chains-depends), its
[`run_remote()`](/development/chain/concepts#run-remote-chaining-chainlets) method can
call this dependency Chainlet, for example, below `HelloAll` we can make calls to
`SayHello`:

```python theme={"system"}
import truss_chains as chains


class HelloAll(chains.ChainletBase):

    def __init__(self, say_hello_chainlet=chains.depends(SayHello)) -> None:
        self._say_hello = say_hello_chainlet

    async def run_remote(self, names: list[str]) -> str:
        output = []
        for name in names:
            output.append(self._say_hello.run_remote(name))
        return "\n".join(output)
```

## Run remote (chaining Chainlets)

The `run_remote()` method is run each time the Chainlet is called. It is the
sole public interface for the Chainlet (though you can have as many private
helper functions as you want) and its inputs and outputs must have type
annotations.

In `run_remote()` you implement the actual work of the Chainlet, such as model
inference or data chunking:

```python theme={"system"}
import truss_chains as chains


class PhiLLM(chains.ChainletBase):
    async def run_remote(self, messages: Messages) -> str:
        import torch

        model_inputs = await self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = await self._tokenizer(model_inputs, return_tensors="pt")
        input_ids = inputs["input_ids"].to("cuda")
        with torch.no_grad():
            outputs = await self._model.generate(
                input_ids=input_ids, **self._generate_args)
            output_text = await self._tokenizer.decode(
                outputs[0], skip_special_tokens=True)
        return output_text
```

We recommend implementing this as an `async` method and using async APIs for
doing all the work (for example, downloads, vLLM or TRT inference).

It is possible to stream results back, see our
[streaming guide](/development/chain/streaming).

<Tip>
  If `run_remote()` makes calls to other Chainlets, for example, invoking a dependency
  Chainlet for each element in a list, you can benefit from concurrent
  execution, by making the `run_remote()` an `async` method and starting the
  calls as concurrent tasks
  `asyncio.create_task(self._dep_chainlet.run_remote(...))`.
</Tip>

## Entrypoint

The entrypoint is called directly from the deployed Chain's API endpoint and
kicks off the entire chain. The entrypoint is also responsible for returning the
final result back to the client.

Using the
[`@chains.mark_entrypoint`](/reference/sdk/chains#function-truss_chains-mark_entrypoint)
decorator, one Chainlet within a file is set as the entrypoint to the chain.

```python theme={"system"}
@chains.mark_entrypoint
class HelloAll(chains.ChainletBase):
```

Optionally you can also set a Chain display name (not to be confused with
Chainlet display name) with this decorator:

```python theme={"system"}
@chains.mark_entrypoint("My Awesome Chain")
class HelloAll(chains.ChainletBase):
```

## I/O and `pydantic` data types

To make orchestrating multiple remotely deployed services possible, Chains
relies heavily on typed inputs and outputs. Values must be serialized to a safe
exchange format to be sent over the network.

The Chains framework uses the type annotations to infer how data should be
serialized and currently is restricted to types that are JSON compatible. Types
can be:

* Direct type annotations for simple types such as `int`, `float`,
  or `list[str]`.
* Pydantic models to define a schema for nested data structures or multiple
  arguments.

An example of pydantic input and output types for a Chainlet is given below:

```python theme={"system"}
import enum
import pydantic


class Modes(enum.Enum):
    MODE_0 = "MODE_0"
    MODE_1 = "MODE_1"


class SplitTextInput(pydantic.BaseModel):
    data: str
    num_partitions: int
    mode: Modes


class SplitTextOutput(pydantic.BaseModel):
    parts: list[str]
    part_lens: list[int]
```

Refer to the [pydantic docs](https://docs.pydantic.dev/latest/) for more
details on how
to define custom pydantic data models.

Also refer to the [guide](/development/chain/binaryio) about efficient integration
of binary and numeric data.

## Chains compared to Truss

<Accordion title="Tips for Truss users" icon="lightbulb">
  Chains is an alternate SDK for packaging and deploying AI models. It carries over many features and concepts from Truss and gives you access to the benefits of Baseten (resource provisioning, autoscaling, fast cold starts, etc), but it is not a 1-1 replacement for Truss.

  Here are some key differences:

  * Rather than running `truss init` and creating a Truss in a directory, a Chain
    is a single file, giving you more flexibility for implementing multi-step
    model inference. Create an example with `truss chains init`.
  * Configuration is done inline in typed Python code rather than in a
    `config.yaml` file.
  * While Chainlets are converted to Truss models when run on Baseten,
    `Chainlet != TrussModel`.

  Chains is designed for compatibility and incremental adoption, with a stub
  function for wrapping existing deployed models.
</Accordion>
