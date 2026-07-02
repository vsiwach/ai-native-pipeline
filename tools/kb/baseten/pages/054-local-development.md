# Local development
Source: https://docs.baseten.co/development/chain/localdev

Iterating, Debugging, Testing, Mocking

Chains run in production as replicated remote deployments, but you can develop
and test them locally first.

<Accordion title="Principles behind Chains">
  Chains exists to help you build multi-step, multi-model pipelines. The
  abstractions that Chains introduces are based on six opinionated principles:
  three for architecture and three for developer experience.

  **Architecture principles**

  <Steps>
    <Step title="Atomic components">
      Each step in the pipeline can set its own hardware requirements and
      software dependencies, separating GPU and CPU workloads.
    </Step>

    <Step title="Modular scaling">
      Each component has independent autoscaling parameters for targeted
      resource allocation, removing bottlenecks from your pipelines.
    </Step>

    <Step title="Maximum composability">
      Components specify a single public interface for flexible-but-safe
      composition and are reusable between projects
    </Step>
  </Steps>

  **Developer experience principles**

  <Steps>
    <Step title="Type safety and validation">
      Eliminate entire taxonomies of bugs by writing typed Python code and
      validating inputs, outputs, module initializations, function signatures,
      and even remote server configurations.
    </Step>

    <Step title="Local debugging">
      Seamless local testing and cloud deployments: test Chains locally with
      support for mocking the output of any step and simplify your cloud
      deployment loops by separating large model deployments from quick
      updates to glue code.
    </Step>

    <Step title="Incremental adoption">
      Use Chains to orchestrate existing model deployments, like pre-packaged
      models from Baseten’s model library, alongside new model pipelines built
      entirely within Chains.
    </Step>
  </Steps>
</Accordion>

Locally, a Chain is just Python files in a source tree. While that gives you a
lot of flexibility in how you structure your code, there are some constraints
and rules to follow to ensure successful distributed, remote execution in
production.

<Tip>
  The best thing you can do while developing locally with Chains is to run your
  code frequently, even if you do not have a  `__main__` section: the Chains
  framework runs various validations at
  <Tooltip>module initialization</Tooltip> to help
  you catch issues early.

  Additionally, running `mypy` and fixing reported type errors can help you
  find problems early in a rapid feedback loop, before attempting a (much
  slower) deployment.
</Tip>

<Tip>
  Complementary to the purely local development Chains also has a "watch" mode,
  like Truss, see the [watch guide](/development/chain/watch).
</Tip>

## Test a Chain locally

Let's revisit our "Hello World" Chain:

```python hello_chain/hello.py theme={"system"}
import asyncio
import truss_chains as chains


# This Chainlet does the work
class SayHello(chains.ChainletBase):

    async def run_remote(self, name: str) -> str:
        return f"Hello, {name}"


# This Chainlet orchestrates the work
@chains.mark_entrypoint
class HelloAll(chains.ChainletBase):

    def __init__(self, say_hello_chainlet=chains.depends(SayHello)) -> None:
        self._say_hello = say_hello_chainlet

    async def run_remote(self, names: list[str]) -> str:
        tasks = []
        for name in names:
            tasks.append(asyncio.create_task(
                self._say_hello.run_remote(name)))
        
        return "\n".join(await asyncio.gather(*tasks))


# Test the Chain locally
if __name__ == "__main__":
    with chains.run_local():
        hello_chain = HelloAll()
        result = asyncio.run(hello_chain.run_remote(["Marius", "Sid", "Bola"]))
        print(result)
```

When the `__main__()` module is run, local instances of the Chainlets are
created, allowing you to test functionality of your chain just by executing the
Python file:

```bash Terminal theme={"system"}
cd hello_chain
python hello.py
# Hello, Marius
# Hello, Sid
# Hello, Bola
```

## Mock execution of GPU Chainlets

Using `run_local()` to run your code locally requires that your development
environment have the compute resources and dependencies that each Chainlet
needs. But that often isn't possible when building with AI models.

Chains offers a workaround, mocking, to let you test the coordination and
business logic of your multi-step inference pipeline without worrying about
running the model locally.

The second example in the [getting started guide](/development/chain/getting-started)
implements a Truss Chain for generating poems with Phi-3.

This Chain has two Chainlets:

1. The `PhiLLM` Chainlet, which can run on NVIDIA GPUs such as the L4.
2. The `PoemGenerator` Chainlet, which easily runs on a CPU.

If you have an NVIDIA T4 under your desk, good for you. For the rest of us, we
can mock the `PhiLLM` Chainlet that is infeasible to run locally so that we can
quickly test the `PoemGenerator` Chainlet.

To do this, we define a mock Phi-3 model in our `__main__` module and give it
a [`run_remote()`](/development/chain/concepts#run-remote-chaining-chainlets) method that
produces a test output that matches the output type we expect from the real
Chainlet. Then, we inject an instance of this mock Chainlet into our Chain:

```python poems.py theme={"system"}
if __name__ == "__main__":
    class FakePhiLLM:
        async def run_remote(self, prompt: str) -> str:
            return f"Here's a poem about {prompt.split(' ')[-1]}"


    with chains.run_local():
        poem_generator = PoemGenerator(phi_llm=FakePhiLLM())
        result = asyncio.run(poem_generator.run_remote(words=["bird", "plane", "superman"]))
        print(result)
```

And run your Python file:

```bash Terminal theme={"system"}
python poems.py
# ['Here's a poem about bird', 'Here's a poem about plane', 'Here's a poem about superman']
```

### Typing of mocks

You may notice that the argument `phi_llm` expects a type `PhiLLM`, while we
pass an instance of `FakePhiLLM`. These aren't the same, which is formally a
type error.

However, this works at runtime because we constructed `FakePhiLLM` to
implement the same *protocol* as the real thing. We can make this explicit by
defining a `Protocol` as a type annotation:

```python theme={"system"}
from typing import Protocol


class PhiProtocol(Protocol):
    def run_remote(self, data: str) -> str:
        ...
```

and changing the argument type in `PoemGenerator`:

```python theme={"system"}
@chains.mark_entrypoint
class PoemGenerator(chains.ChainletBase):
    def __init__(self, phi_llm: PhiProtocol = chains.depends(PhiLLM)) -> None:
        self._phi_llm = phi_llm
```

The `Protocol` annotation is optional; it makes the typing consistency explicit.
