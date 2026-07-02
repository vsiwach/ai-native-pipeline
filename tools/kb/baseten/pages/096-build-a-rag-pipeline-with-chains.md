# Build a RAG pipeline with Chains
Source: https://docs.baseten.co/examples/chains-build-rag

Combine retrieval and generation into a single compound workflow.

[Learn more about Chains](/development/chain/overview)

## Prerequisites

You need [uv](https://docs.astral.sh/uv/) installed and a [Baseten account](https://app.baseten.co/signup) with an [API key](https://app.baseten.co/settings/account/api_keys).

If you want to run this example in
[local debugging mode](/development/chain/localdev#test-a-chain-locally), you'll also need to
install chromadb:

```shell theme={"system"}
uv pip install chromadb
```

The complete code used in this tutorial can also be found in the
[Chains examples repo](https://github.com/basetenlabs/truss/tree/main/truss-chains/examples/rag).

# Overview

Retrieval-augmented generation (RAG) is a multi-model pipeline for generating
context-aware answers from LLMs.

There are a number of ways to build a RAG system. This tutorial shows a minimum
viable implementation with a basic vector store and retrieval function. It's
intended as a starting point to show how Chains helps you flexibly combine model
inference and business logic.

In this tutorial, we'll build a simple RAG pipeline for a hypothetical alumni
matching service for a university. The system:

1. Takes a bio with information about a new graduate
2. Uses a vector database to retrieve semantically similar bios of other alums
3. Uses an LLM to explain why the new graduate should meet the selected alums
4. Returns the writeup from the LLM

## Build the Chain

Create a file `rag.py` in a new directory with:

```sh theme={"system"}
mkdir rag
touch rag/rag.py
cd rag
```

Our RAG Chain is composed of three parts:

* `VectorStore`, a Chainlet that implements a vector database with a retrieval
  function.
* `LLMClient`, a Stub for connecting to a deployed LLM.
* `RAG`, the entrypoint Chainlet that orchestrates the RAG pipeline and
  has `VectorStore` and `LLMClient` as dependencies.

We'll examine these components one by one and then see how they all work
together.

### Vector store Chainlet

A real production RAG system would use a hosted vector database with a massive
number of stored embeddings. For this example, we're using a small local vector
store built with `chromadb` to stand in for a more complex system.

The Chainlet has three parts:

* [`remote_config`](/reference/sdk/chains#remote-configuration), which
  configures a Docker image on deployment with dependencies.
* `__init__()`, which runs once when the Chainlet is spun up, and creates the
  vector database with ten sample bios.
* [`run_remote()`](/development/chain/concepts#run-remote-chaining-chainlets), which runs
  each time the Chainlet is called and is the sole public interface for the
  Chainlet.

```python rag/rag.py theme={"system"}
import truss_chains as chains


# Create a Chainlet to serve as our vector database.
class VectorStore(chains.ChainletBase):
    # Add chromadb as a dependency for deployment.
    remote_config = chains.RemoteConfig(
        docker_image=chains.DockerImage(
            pip_requirements=["chromadb"]
        )
    )
    # Runs once when the Chainlet is deployed or scaled up.
    def __init__(self):
        # Import Chainlet-specific dependencies in init, not at the top of
        # the file.
        import chromadb
        self._chroma_client = chromadb.EphemeralClient()
        self._collection = self._chroma_client.create_collection(name="bios")
        # Sample documents are hard-coded for your convenience
        documents = [
            "Angela Martinez is a tech entrepreneur based in San Francisco. As the founder and CEO of a successful AI startup, she is a leading figure in the tech community. Outside of work, Angela enjoys hiking the trails around the Bay Area and volunteering at local animal shelters.",
            "Ravi Patel resides in New York City, where he works as a financial analyst. Known for his keen insight into market trends, Ravi spends his weekends playing chess in Central Park and exploring the city's diverse culinary scene.",
            "Sara Kim is a digital marketing specialist living in San Francisco. She helps brands build their online presence with creative strategies. Outside of work, Sara is passionate about photography and enjoys hiking the trails around the Bay Area.",
            "David O'Connor calls New York City his home and works as a high school teacher. He is dedicated to inspiring the next generation through education. In his free time, David loves running along the Hudson River and participating in local theater productions.",
            "Lena Rossi is an architect based in San Francisco. She designs sustainable and innovative buildings that contribute to the city's skyline. When she's not working, Lena enjoys practicing yoga and exploring art galleries.",
            "Akio Tanaka lives in Tokyo and is a software developer specializing in mobile apps. Akio is an avid gamer and enjoys attending eSports tournaments. He also has a passion for cooking and often experiments with new recipes in his spare time.",
            "Maria Silva is a nurse residing in New York City. She is dedicated to providing compassionate care to her patients. Maria finds joy in gardening and often spends her weekends tending to her vibrant flower beds and vegetable garden.",
            "John Smith is a journalist based in San Francisco. He reports on international politics and has a knack for uncovering compelling stories. Outside of work, John is a history buff who enjoys visiting museums and historical sites.",
            "Aisha Mohammed lives in Tokyo and works as a graphic designer. She creates visually stunning graphics for a variety of clients. Aisha loves to paint and often showcases her artwork in local exhibitions.",
            "Carlos Mendes is an environmental engineer in San Francisco. He is passionate about developing sustainable solutions for urban areas. In his leisure time, Carlos enjoys surfing and participating in beach clean-up initiatives."
        ]
        # Add all documents to the database
        self._collection.add(
            documents=documents,
            ids=[f"id{n}" for n in range(len(documents))]
        )

    # Runs each time the Chainlet is called
    async def run_remote(self, query: str) -> list[str]:
        # This call to includes embedding the query string.
        results = self._collection.query(query_texts=[query], n_results=2)
        if results is None or not results:
            raise ValueError("No bios returned from the query")
        if not results["documents"] or not results["documents"][0]:
            raise ValueError("Bios are empty")
        return results["documents"][0]
```

### LLM inference stub

Now that we can retrieve relevant bios from the vector database, we need to pass
that information to an LLM to generate our final output.

Chains can integrate previously deployed models using a Stub. Like Chainlets,
Stubs implement
[`run_remote()`](/development/chain/concepts#run-remote-chaining-chainlets), but as a call
to the deployed model.

For our LLM, we'll use Phi-3 Mini Instruct, a small-but-mighty open source LLM.

<Card title="Deploy Phi-3 Mini Instruct 4k" icon="rocket" href="https://www.baseten.co/library/phi-3-mini-4k-instruct/">
  One-click model deployment from Baseten's model library.
</Card>

While the model is deploying, be sure to note down the models' invocation URL from
the model dashboard for use in the next step.

To use our deployed LLM in the RAG Chain, we define a Stub:

```python rag/rag.py theme={"system"}
class LLMClient(chains.StubBase):
    # Runs each time the Stub is called
    async def run_remote(self, new_bio: str, bios: list[str]) -> str:
        # Use the retrieved bios to augment the prompt -- here's the "A" in RAG!
        prompt = f"""You are matching alumni of a college to help them make connections. Explain why the person described first would want to meet the people selected from the matching database.
        Person you're matching: {new_bio}
        People from database: {" ".join(bios)}"""
        # Call the deployed model.
        resp = await self._remote.predict_async(json_payload={
            "messages": [{"role": "user", "content": prompt}],
            "stream"  : False
        })
        return resp["output"][len(prompt) :].strip()
```

### RAG entrypoint Chainlet

The entrypoint to a Chain is the Chainlet that specifies the public-facing input
and output of the Chain and orchestrates calls to dependencies.

The `__init__` function in this Chainlet takes two new arguments:

* Add dependencies to any Chainlet with
  [`chains.depends()`](/reference/sdk/chains#function-truss_chains-depends). Only
  Chainlets, not Stubs, need to be added in this fashion.
* Use
  [`chains.depends_context()`](/reference/sdk/chains#function-truss_chains-depends_context)
  to inject a context object at runtime. This context object is required to
  initialize the `LLMClient` stub.
* Visit your [baseten workspace](https://app.baseten.co/models) to find your
  the URL of the previously deployed Phi-3 model and insert if as value
  for `LLM_URL`.

```python rag/rag.py theme={"system"}
# Insert the URL from the previously deployed Phi-3 model.
LLM_URL = ...

@chains.mark_entrypoint
class RAG(chains.ChainletBase):

    # Runs once when the Chainlet is spun up
    def __init__(
        self,
        # Declare dependency chainlets.
        vector_store: VectorStore = chains.depends(VectorStore),
        context: chains.DeploymentContext = chains.depends_context(),
    ):
        self._vector_store = vector_store
        # The stub needs the context for setting up authentication.
        self._llm = LLMClient.from_url(LLM_URL, context)

    # Runs each time the Chain is called
    async def run_remote(self, new_bio: str) -> str:
        # Use the VectorStore Chainlet for context retrieval.
        bios = await self._vector_store.run_remote(new_bio)
        # Use the LLMClient Stub for augmented generation.
        contacts = await self._llm.run_remote(new_bio, bios)
        return contacts
```

## Test locally

Because our Chain uses a Stub for the LLM call, we can run the whole Chain
locally without any GPU resources.

Before running the Chainlet, make sure to set your Baseten API key as an
environment variable `BASETEN_API_KEY`.

```python rag/rag.py theme={"system"}
if __name__ == "__main__":
    import os
    import asyncio

    with chains.run_local(
        # This secret is needed even locally, because part of this chain
        # calls the separately deployed Phi-3 model. Only the Chainlets
        # actually run locally.
        secrets={"baseten_chain_api_key": os.environ["BASETEN_API_KEY"]}
    ):
        rag_client = RAG()
        result = asyncio.run(rag_client.run_remote(
            """
            Sam just moved to Manhattan for his new job at a large bank.
            In college, he enjoyed building sets for student plays.
            """
        ))
        print(result)
```

We can run our Chain locally:

```sh theme={"system"}
python rag.py
```

After a few moments, we should get a recommendation for why Sam should meet the
alumni selected from the database.

## Deploy to production

Once we're satisfied with our Chain's local behavior, we can deploy it to
Baseten. To deploy the Chain, run:

```sh theme={"system"}
truss chains push rag.py
```

This deploys the Chain as a published deployment. Once it's running, call it
from its API endpoint.

You can do this in the console with cURL:

```sh theme={"system"}
curl -X POST 'https://chain-5wo86nn3.api.baseten.co/production/run_remote' \
    -H "Authorization: Bearer $BASETEN_API_KEY" \
    -d '{"new_bio": "Sam just moved to Manhattan for his new job at a large bank.In college, he enjoyed building sets for student plays."}'
```

Alternatively, you can also integrate this in a Python application:

```python call_chain.py theme={"system"}
import requests
import os

# Insert the URL from the deployed rag chain. You can get it from the CLI
# output or the status page, e.g.
# "https://chain-6wgeygoq.api.baseten.co/production/run_remote".
RAG_CHAIN_URL = ""
baseten_api_key = os.environ["BASETEN_API_KEY"]

if not RAG_CHAIN_URL:
    raise ValueError("Please insert the URL for the RAG chain.")

resp = requests.post(
    RAG_CHAIN_URL,
    headers={"Authorization": f"Bearer {baseten_api_key}"},
    json={"new_bio": new_bio},
)

print(resp.json())
```

The published deployment has access to full autoscaling settings and will
scale to zero when not in use.

To iterate on the Chain during development, use `truss chains push --watch rag.py`
to create a development deployment with live code patching.
