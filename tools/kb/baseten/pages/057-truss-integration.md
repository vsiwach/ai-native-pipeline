# Truss integration
Source: https://docs.baseten.co/development/chain/stub

Integrate deployed Truss models with stubs

Chains can be combined with existing Truss models using Stubs.

A Stub acts as a substitute (client-side proxy) for a remotely deployed
dependency, either a Chainlet or a Truss model. The Stub performs the remote
invocations as if it were local by taking care of the transport layer,
authentication, data serialization and retries.

Stubs can be integrated into Chainlets by passing in a URL of the deployed
model. They also require
[`context`](/development/chain/concepts#context-access-information) to be initialized
(for authentication).

The following Chainlet wraps a deployed model with a Stub:

```python my_chainlet.py theme={"system"}
import truss_chains as chains


class LLMClient(chains.StubBase):

    async def run_remote(self, prompt: str) -> str:
        # Call the deployed model
        resp = await self.predict_async(inputs={
            "messages": [{"role": "user", "content": prompt}],
            "stream"  : False
        })
        # Return a string with the model output
        return resp["output"]


LLM_URL = ...


class MyChainlet(chains.ChainletBase):

    def __init__(
        self,
        context: chains.DeploymentContext = chains.depends_context(),
    ):
        self._llm = LLMClient.from_url(LLM_URL, context)
```

There are various ways how you can make a call to the other deployment:

* Input as JSON dict (like above) or pydantic model.
* Automatic parsing of the response into a pydantic model using the
  `output_model` argument.
* `predict_async` (recommended) or `predict_sync`.
* Streaming responses using `predict_async_stream` which returns an async
  bytes iterator.
* Customized with `RPCOptions`.

See the
[StubBase reference](/reference/sdk/chains#class-truss_chains-stubbase)
for all APIs.
