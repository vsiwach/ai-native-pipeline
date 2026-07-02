# Concepts
Source: https://docs.baseten.co/loops/concepts

How Loops sessions, trainers, samplers, and checkpoints fit together.

A Loops session pairs a trainer server with a sampling server so that trained weights move to the sampler as soon as they exist. The trainer runs forward, backward, and optimizer steps; the sampler generates from current weights. Both live inside the same session and share a weight-sync path from the moment you provision them.

Unlike offline training, where you finish a run, save a checkpoint, and then reload weights into a separate inference process, Loops keeps the sampler in sync throughout. When the trainer saves weights, the sampling server picks them up without restarting. The sampler you query at step 100 is running the same weights the trainer committed.

## Sessions

A Loops session is the container resource that scopes a training project's work. It holds the trainer server and sampling server for a given base model and links them to a Baseten training project. Everything you create within a session (trainer servers, sampling servers, checkpoints) is queryable through that session's ID. For the full route reference, see the [Loops API overview](/reference/loops-api/overview).

## Trainer servers

A trainer server is the process that runs the training computation: forward pass, backward pass, and optimizer step. It owns the model weights for the duration of the session and writes checkpoints to a dedicated storage path under a `bt://loops:…` URI; the [Checkpoints](#checkpoints) section covers the format. There is one trainer per session per base model.

You don't size the trainer yourself. It defaults to the longest sequence length the base model supports, and Baseten picks the GPU type, GPU count, and node topology (single-node or multi-node) to match. When you call [`POST /v1/loops/runs`](/reference/loops-api/runs/create-a-run), Baseten provisions the trainer alongside its paired sampler and returns both resource IDs.

The API route calls a trainer a "run". Both the HTTP API and the SDK identify it by its run ID: the API takes a `run_id` query parameter, and the SDK exposes the same value as [`TrainingClient.run_id`](/reference/sdk/loops/training-client).

## Sampling servers

A sampling server runs inference from the trainer's current weights. It's provisioned alongside the trainer and linked to it at creation time. The sampler receives new weights through the weight-sync runtime whenever the trainer saves them. See [How weight sync works](#how-weight-sync-works) for the mechanism. Because the sampler doesn't restart during a session, generation latency stays low even as weights change, and you can interleave training steps and rollout calls without coordinating reloads.

## Checkpoints

Every time the trainer saves weights, Loops creates a checkpoint identified by a `bt://loops:<run_id>/(weights|sampler_weights)/<checkpoint_name>` URI. The URI encodes the run ID, the checkpoint target (trainer weights or sampler weights), and the checkpoint name, for example, `bt://loops:k4q95w5/weights/step-100`. You pass this URI to create a trainer or sampler server from a prior checkpoint, or to deploy weights to inference.

Checkpoints are stored as folders on disk, not as single archives. Listing checkpoint files returns a paginated response of presigned URLs, one URL per file in the folder, controlled by `page_size` and `page_token` query parameters. This differs from Tinker's single-archive download shape: Tinker returns one URL you download and unpack; Loops returns a page of per-file URLs you fetch individually. If your client code unpacks a Tinker archive today, you'll need to adapt it to iterate the paginated file list instead. The route is [`GET /v1/loops/checkpoints/{checkpoint_id}/files`](/reference/loops-api/checkpoints/get-checkpoint-files).

## Deployments

A Loops deployment is the trainer and sampler you create at the start of a session. They stay live as you train, and weights you commit stream into the sampler in place, with no separate deploy step for inference.

Start a deployment with [`truss loops push <base_model>`](/reference/cli/loops/loops-cli#push). Shut it down with [`truss loops deactivate <deployment_id>`](/reference/cli/loops/loops-cli#deactivate), using the deployment ID from [`truss loops view`](/reference/cli/loops/loops-cli#view).

## Reuse infrastructure across sessions

By default, every new `ServiceClient` creates a fresh session, which provisions a new trainer and sampler. Each re-run of a script pays the full cold-start cost.

A session can opt in to reusing a prior session's trainer and sampler instead of provisioning new ones. Three equivalent surfaces:

* **SDK kwarg**: `tinker.ServiceClient(reuse_from_session_id="2qjl22w")`.
* **Environment variable**: `LOOPS_REUSE_FROM_SESSION_ID=2qjl22w`. `ServiceClient` reads this when no kwarg is passed.
* **HTTP request**: `reuse_from_session_id` field on [`POST /v1/loops/runs`](/reference/loops-api/runs/create-a-run) and [`POST /v1/loops/samplers`](/reference/loops-api/samplers/create-a-sampler).

Reuse is best-effort. The named session must belong to the same team. If the prior trainer is stopped, failed, or unhealthy, the backend falls back to provisioning fresh and the call still succeeds. See [Skip the cold start on re-runs](/loops/quickstart#skip-the-cold-start-on-re-runs) for the script workflow.

## How weight sync works

When a trainer saves weights, the paired sampling server picks them up through a vLLM plugin. The plugin handles the sync without restarting the sampler, so generation can resume immediately at the new weights.

## Supported base models

Loops supports a curated set of Hugging Face base models with verified LoRA configurations. See [Supported base models](/loops/supported-models) for the current list and sequence-length limits.
