# Error handling
Source: https://docs.baseten.co/development/chain/errorhandling

Understanding and handling Chains errors

Error handling in Chains follows the principle that the root cause bubbles
up to the entrypoint, which returns an error response. This works like
Python stack traces, which contain all the layers from where an exception was
raised up to the main function.

Consider the case of a Chain where the entrypoint calls `run_remote` of a
Chainlet named `TextToNum` and this in turn invokes `TextReplicator`. The
respective `run_remote` methods might also use other helper functions that
appear in the call stack.

Below is an example stack trace that shows how the root cause (a
`ValueError`) is propagated up to the entrypoint's `run_remote` method (this
is what you would see as an error log):

```text theme={"system"}
Chainlet-Traceback (most recent call last):
  File "/packages/itest_chain.py", line 132, in run_remote
    value = self._accumulate_parts(text_parts.parts)
  File "/packages/itest_chain.py", line 144, in _accumulate_parts
    value += self._text_to_num.run_remote(part)
ValueError: (showing chained remote errors, root error at the bottom)
├─ Error in dependency Chainlet `TextToNum`:
│   Chainlet-Traceback (most recent call last):
│     File "/packages/itest_chain.py", line 87, in run_remote
│       generated_text = self._replicator.run_remote(data)
│   ValueError: (showing chained remote errors, root error at the bottom)
│   ├─ Error in dependency Chainlet `TextReplicator`:
│   │   Chainlet-Traceback (most recent call last):
│   │     File "/packages/itest_chain.py", line 52, in run_remote
│   │       validate_data(data)
│   │     File "/packages/itest_chain.py", line 36, in validate_data
│   │       raise ValueError(f"This input is too long: {len(data)}.")
╰   ╰   ValueError: This input is too long: 100.
```

## Exception handling and retries

The stack trace above is what you see if you don't catch the exception. It is
possible to add error handling around each remote Chainlet invocation.

Chains tries to raise the same exception class on the *caller* Chainlet as was
raised in the *dependency* Chainlet.

* Builtin exceptions (for example, `ValueError`) always work.
* Custom or third-party exceptions (for example, from `torch`) can be only raised
  in the caller if they are included in the dependencies of the caller as
  well. If the exception class cannot be resolved, a
  `GenericRemoteException` is raised instead.

The *message* of re-raised exceptions is the concatenation
of the original message and the formatted stack trace of the dependency
Chainlet.

Retry a remote invocation when it fails for transient reasons such as networking. Configure retries with `depends` [options](/reference/sdk/chains#function-truss_chains-depends).

Below example shows how you can add automatic retries and error handling for
the call to `TextReplicator` in `TextToNum`:

```python text_to_num.py theme={"system"}
import truss_chains as chains


class TextToNum(chains.ChainletBase):

    def __init__(
        self,
        replicator: TextReplicator = chains.depends(TextReplicator, retries=3),
    ) -> None:
        self._replicator = replicator

    async def run_remote(self, data: ...):
        try:
            generated_text = await self._replicator.run_remote(data)
        except ValueError:
            ...  # Handle error.

```

## Stack filtering

The stack trace is intended to show the user implemented code in
`run_remote` (and user implemented helper functions). Under the
hood, the calls from one Chainlet to another go through an HTTP
connection, managed by the Chains framework. And each Chainlet itself is
run as a FastAPI server with several layers of request handling code "above".

To provide concise, readable stacks, all of this non-user code is
filtered out.
