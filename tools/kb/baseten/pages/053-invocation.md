# Invocation
Source: https://docs.baseten.co/development/chain/invocation

Call your deployed Chain

Once your Chain is deployed, you can call it through its API endpoint. Chains use
the same inference API as models:

* [Environment endpoint](/reference/inference-api/predict-endpoints/environments-run-remote)
* [Development endpoint](/reference/inference-api/predict-endpoints/development-run-remote)
* [Endpoint by ID](/reference/inference-api/predict-endpoints/deployment-run-remote)

Here's an example which calls the development deployment:

```python call_chain.py theme={"system"}
import requests
import os

# From the Chain overview page on Baseten
# E.g. "https://chain-<CHAIN_ID>.api.baseten.co/development/run_remote"
CHAIN_URL = ""
baseten_api_key = os.environ["BASETEN_API_KEY"]
# JSON keys and types match the `run_remote` method signature.
data = {...}

resp = requests.post(
    CHAIN_URL,
    headers={"Authorization": f"Bearer {baseten_api_key}"},
    json=data,
)

print(resp.json())
```

## How to pass chain input

The data schema of the inference request corresponds to the function
signature of [`run_remote()`](/development/chain/concepts#run-remote-chaining-chainlets)
in your entrypoint Chainlet.

For example, for the Hello Chain, `HelloAll.run_remote()`:

```python theme={"system"}
async def run_remote(self, names: list[str]) -> str:
```

You'd pass the following JSON payload:

```json Payload theme={"system"}
{ "names": ["Marius", "Sid", "Bola"] }
```

That is, the keys in the JSON record match the argument names, and values
match the types of `run_remote`.

## Async chain inference

Like Truss models, Chains support async invocation. The [guide for
models](/inference/async) applies largely. In particular for how to wrap the
input and set up the webhook to process results.

The following additional points are chains specific:

* Use chain-based URLS:
  * `https://chain-{chain}.api.baseten.co/production/async_run_remote`
  * `https://chain-{chain}.api.baseten.co/development/async_run_remote`
  * `https://chain-{chain}.api.baseten.co/deployment/{deployment}/async_run_remote`.
  * `https://chain-{chain}.api.baseten.co/environments/{env_name}/async_run_remote`.
* Only the entrypoint is invoked asynchronously. Internal Chainlet-Chainlet
  calls run synchronously.
