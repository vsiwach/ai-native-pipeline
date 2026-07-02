# Loops SDK reference
Source: https://docs.baseten.co/reference/sdk/loops/overview

Python client for Loops: ServiceClient, TrainingClient, SamplingClient, types, and errors.

The Loops Python SDK runs LoRA training on Baseten from Python. For installation and an end-to-end walkthrough, see the [Loops quickstart](/loops/quickstart). This reference documents each class and type.

## Clients

* [`ServiceClient`](/reference/sdk/loops/service-client): provision trainer and sampling servers, manage the session, and list checkpoints.
* [`TrainingClient`](/reference/sdk/loops/training-client): run forward and backward passes, optimizer steps, and publish weights.
* [`SamplingClient`](/reference/sdk/loops/sampling-client): generate completions from current or version-pinned weights.

## Commonly used methods

* [`create_lora_training_client()`](/reference/sdk/loops/service-client): provision a trainer and get a `TrainingClient`.
* [`forward_backward()`](/reference/sdk/loops/training-client) and [`optim_step()`](/reference/sdk/loops/training-client): run one training step.
* [`save_state()`](/reference/sdk/loops/training-client): save a checkpoint.
* [`save_weights_and_get_sampling_client()`](/reference/sdk/loops/training-client): publish weights and get a pinned `SamplingClient`.
* [`sample()`](/reference/sdk/loops/sampling-client): generate from the trained model.
* [`list_checkpoints()`](/reference/sdk/loops/training-client): list a run's checkpoints.

## Reference

* [Types](/reference/sdk/loops/types): training inputs, configuration, and result handles.
* [Errors](/reference/sdk/loops/errors): the SDK exception types and when each is raised.

## Tinker compatibility

Install with the `[tinker]` extra and `import tinker` to run existing Tinker training scripts unchanged. For the mapped names and behavioral differences, see the [Tinker compatibility guide](/loops/tinker-compatibility).
