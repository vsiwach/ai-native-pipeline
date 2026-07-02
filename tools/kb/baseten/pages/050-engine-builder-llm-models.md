# Engine Builder LLM models
Source: https://docs.baseten.co/development/chain/engine-builder-models

Engine-Builder LLM models are pre-trained models that are optimized for specific inference tasks.

Baseten's [Engine-Builder](/engines/engine-builder-llm/overview) enables the deployment of optimized model inference engines. Currently, it supports TensorRT-LLM. Truss Chains lets you use these engines as Chainlets.

## Llama 7B example

Use the `EngineBuilderLLMChainlet` baseclass to configure an LLM engine. The additional `engine_builder_config` field specifies model architecture, repository, engine parameters, and more; the full options are detailed in the [Engine-Builder configuration guide](/engines/engine-builder-llm/engine-builder-config).

Define the engine-backed Chainlet:

```python llama_7b_chainlet.py theme={"system"}
import truss_chains as chains
from truss.base import trt_llm_config, truss_config

class Llama7BChainlet(chains.EngineBuilderLLMChainlet):
    remote_config = chains.RemoteConfig(
        compute=chains.Compute(gpu=truss_config.Accelerator.H100),
        assets=chains.Assets(secret_keys=["hf_access_token"]),
    )
    engine_builder_config = truss_config.TRTLLMConfiguration(
        build=trt_llm_config.TrussTRTLLMBuildConfiguration(
            base_model=trt_llm_config.TrussTRTLLMModel.LLAMA,
            checkpoint_repository=trt_llm_config.CheckpointRepository(
                source=trt_llm_config.CheckpointSource.HF,
                repo="meta-llama/Llama-3.1-8B-Instruct",
            ),
            max_batch_size=8,
            max_seq_len=4096,
            tensor_parallel_count=1,
        )
    )
```

## Differences from standard Chainlets

* No `run_remote` implementation: Unlike regular Chainlets, `EngineBuilderLLMChainlet` doesn't require users to implement `run_remote()`. Instead, it automatically wires into the deployed engine's API. All LLM Chainlets have the same function signature: `chains.EngineBuilderLLMInput` as input and a stream (`AsyncIterator`) of strings as output. Likewise, `EngineBuilderLLMChainlet`s can only be used as dependencies, but can't have dependencies themselves.
* No `run_local` ([guide](/development/chain/localdev)) or `watch` ([guide](/development/chain/watch)). Standard Chains support a local debugging mode and watch; however, when using `EngineBuilderLLMChainlet`, local execution isn't available, and testing must be done after deployment.
  For a faster dev loop of the rest of your chain (everything except the engine-builder Chainlet), you can substitute those Chainlets with stubs, as you can for an already-deployed Truss model ([guide](/development/chain/stub)).

## Integrate the Engine-Builder chainlet

After defining an `EngineBuilderLLMChainlet` like `Llama7BChainlet` above, you can use it as a dependency in other conventional Chainlets:

```python controller.py theme={"system"}
from typing import AsyncIterator
import truss_chains as chains

@chains.mark_entrypoint
class TestController(chains.ChainletBase):
    """Example using the Engine-Builder Chainlet in another Chainlet."""

    def __init__(self, llm=chains.depends(Llama7BChainlet)) -> None:
        self._llm = llm

    async def run_remote(self, prompt: str) -> AsyncIterator[str]:
        messages = [{"role": "user", "content": prompt}]
        llm_input = chains.EngineBuilderLLMInput(messages=messages)
        async for chunk in self._llm.run_remote(llm_input):
            yield chunk
```
