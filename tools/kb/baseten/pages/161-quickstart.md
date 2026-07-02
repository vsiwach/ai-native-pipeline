# Quickstart
Source: https://docs.baseten.co/loops/quickstart

Train one step with Loops, sample from the tuned weights, and shut the session down.

Use the Loops Python SDK to create a LoRA training run, save a checkpoint, generate text from those weights, and list the checkpoint from both Python and the HTTP API. At the end, you shut down the servers you provisioned. The base model throughout is `Qwen/Qwen3.5-2B`, one of the [supported base models](/loops/supported-models).

## Prerequisites

* **Python 3.12+ and [uv](https://docs.astral.sh/uv/)**: The quickstart uses `uv` to install the Loops client and run the training script.
* **API key**: A [workspace API key](/organization/api-keys) with org access to Loops, exported as `BASETEN_API_KEY`.

<Note>
  Loops is in early access. To enable it for your workspace, [fill out the signup form](https://www.baseten.co/talk-to-us/loops-signup/).
</Note>

## Install

Install `baseten-loops` with the `[tinker]` extra into a uv project. Create one first if you don't have it:

```bash theme={"system"}
uv init loops-quickstart
cd loops-quickstart
uv add 'baseten-loops[tinker]'
```

The `[tinker]` extra pulls in `baseten-loops-tinker`, which re-exports the public API under the `tinker` namespace so existing `import tinker` scripts run unchanged.

Verify the install by running `uv run python train_loops.py`:

<CodeGroup>
  ```python train_loops.py theme={"system"}
  import tinker
  from importlib.metadata import version

  print(tinker.ServiceClient)
  print("baseten-loops-tinker", version("baseten-loops-tinker"))
  ```

  ```output Output theme={"system"}
  <class 'tinker._service_client.ServiceClient'>
  baseten-loops-tinker x.x.x
  ```
</CodeGroup>

The printed class path and resolved `baseten-loops-tinker` version confirm Baseten's Tinker compatibility package is installed, not the upstream `tinker` package.

## Provision a trainer

A Loops session pairs a trainer server (forward, backward, and optimizer steps) with a sampling server (generates from current weights). Constructing a [`ServiceClient`](/reference/sdk/loops/service-client) and calling [`create_lora_training_client()`](/reference/sdk/loops/service-client) provisions both and returns a [`TrainingClient`](/reference/sdk/loops/training-client). The call blocks until the trainer is ready, which can take several minutes for a fresh base model.

Replace the contents of `train_loops.py` with the provision step:

```python train_loops.py theme={"system"}
import tinker

BASE_MODEL = "Qwen/Qwen3.5-2B"

service_client = tinker.ServiceClient()
training_client = service_client.create_lora_training_client(
    base_model=BASE_MODEL,
    rank=16,
)

print(f"session_id={service_client.session_id}")
print(f"run_id={training_client.run_id}")
```

You'll append the training, sampling, and listing steps to this same file in the next three sections, then run the whole thing once at the end.

Provisioning starts GPU servers in your workspace that keep running after your script exits, so plan to finish with the [shut down step](#shut-down-the-session) below.

## Run a training round trip

The smallest complete round trip is one forward pass, one backward pass, one optimizer step, and one weight save. The block below mirrors the canonical supervised fine-tuning (SFT) example: it tokenizes a prompt-and-answer pair, masks the prompt positions from the loss, runs the round trip, and saves a named checkpoint.

Append to `train_loops.py`:

```python train_loops.py theme={"system"}
def build_sft_datum(tokenizer, prompt, answer):
    p = tokenizer.encode(prompt, add_special_tokens=False)
    a = tokenizer.encode(answer, add_special_tokens=False)
    # Loops/tinker forward_backward does NOT shift labels internally (unlike HF
    # Trainer). Shift here so logits at position i predict token i+1:
    # drop the final input token and the first prompt mask position.
    full = p + a
    tokens = full[:-1]
    targets = [-100] * (len(p) - 1) + list(a)  # mask prompt, supervise answer
    return tokens, targets

tokens, targets = build_sft_datum(
    training_client.get_tokenizer(),
    prompt="What is the capital of France?\nAnswer:",
    answer=" Paris",
)
datum = tinker.Datum(
    model_input=tinker.ModelInput.from_ints(tokens),
    loss_fn_inputs={
        "target_tokens": tinker.TensorData(
            data=targets, dtype="int64", shape=[len(targets)]
        )
    },
)

fb = training_client.forward_backward(data=[datum]).result(timeout=600.0)
print(f"loss={fb.loss:.6f}")

optim = training_client.optim_step(
    tinker.AdamParams(learning_rate=4e-5)
).result(timeout=600.0)
print(f"optim_metrics={optim.metrics}")

save_resp = training_client.save_weights_for_sampler(name="step-1").result(timeout=600.0)
print(f"saved checkpoint at {save_resp.path}")
```

[`forward_backward()`](/reference/sdk/loops/training-client) is the first training operation you submit after provisioning. [`save_weights_for_sampler()`](/reference/sdk/loops/training-client) publishes a sampler checkpoint under `sampler_weights/` that you can deploy to inference. This checkpoint omits optimizer state, so you can't resume training from it; use [`save_state()`](/reference/sdk/loops/training-client) when you need a resumable checkpoint.

## Sample from the tuned weights

The checkpoint you saved is already on the paired sampler, so you can generate from it without deploying anything. [`create_sampling_client()`](/reference/sdk/loops/training-client) takes the [`bt://` URI](/loops/concepts#checkpoints) that `save_weights_for_sampler()` returned and binds a [`SamplingClient`](/reference/sdk/loops/sampling-client) to those weights. Append to `train_loops.py`:

```python train_loops.py theme={"system"}
tokenizer = training_client.get_tokenizer()
sampling_client = training_client.create_sampling_client(model_path=save_resp.path)

sample = sampling_client.sample(
    prompt=tinker.ModelInput.from_ints(
        tokenizer.encode("What is the capital of France?\nAnswer:", add_special_tokens=False)
    ),
    num_samples=1,
    sampling_params=tinker.SamplingParams(max_tokens=8),
)
print(f"completion={tokenizer.decode(sample.sequences[0].tokens)!r}")
```

One optimizer step barely changes a 2B model, so the completion reads like base-model output. Still, the sampler served the `step-1` weights your trainer published seconds earlier, without a restart or a deploy step in between. In a longer run, this same call is how you evaluate checkpoints mid-training.

## List checkpoints

Every `save_weights_for_sampler()` call creates a checkpoint. The bound `TrainingClient` lists them with [`list_checkpoints()`](/reference/sdk/loops/training-client), no arguments needed. Append to `train_loops.py`:

```python train_loops.py theme={"system"}
for ckpt in training_client.list_checkpoints():
    print(ckpt.id, ckpt.checkpoint_id, ckpt.created_at)
```

Now run the full script. Output values vary, but a successful run prints a session ID, run ID, loss, optimizer metrics, saved checkpoint URI, a sampled completion, and one listed checkpoint:

```bash theme={"system"}
uv run python train_loops.py
```

```output theme={"system"}
session_id=2qjl22w
run_id=e3mvjo3
loss=2.456638
optim_metrics={'step': 1.0, 'learning_rate': 4e-05, 'lr': 4e-05, 'grad_norm': 74.11, ...}
saved checkpoint at bt://loops:e3mvjo3/sampler_weights/step-1
completion=' 1. France is a country in'
VqKXRGB step-1 2026-07-01 20:50:39.854000+00:00
```

You might also see warnings from `transformers` about PyTorch being unavailable and from the Hugging Face Hub about unauthenticated requests. Both are harmless here: the client only uses `transformers` for tokenization, and the tokenizer download works without a token.

The HTTP API returns the same listing for scripts and CI pipelines that don't run Python. Use the `run_id` your script printed when provisioning. The response includes the same globally unique `id` and checkpoint name:

<CodeGroup>
  ```bash Request theme={"system"}
  curl --request GET \
    --url "https://api.baseten.co/v1/loops/checkpoints?run_id=<run_id>" \
    --header "Authorization: Bearer $BASETEN_API_KEY"
  ```

  ```json Output theme={"system"}
  {
    "checkpoints": [
      {
        "checkpoint_id": "step-1",
        "created_at": "2026-07-01T20:50:39.854Z",
        "checkpoint_type": "lora",
        "base_model": "Qwen/Qwen3.5-2B",
        "lora_adapter_config": {
          "r": 16
        },
        "size_bytes": 33638400,
        "sync_status": null,
        "id": "VqKXRGB",
        "run_id": "e3mvjo3",
        "target": "sampler"
      }
    ]
  }
  ```
</CodeGroup>

To fetch the weight files, call [`get_checkpoint_archive_url()`](/reference/sdk/loops/training-client) with the globally unique `id` value as the `checkpoint_id` argument. From a separate Python session where `training_client` isn't in scope, construct `tinker.ServiceClient()` and call the same method on it.

## Skip the cold start on re-runs

Your first run provisioned a trainer and sampler. The second run doesn't have to. Grab the `session_id` your script printed (`session_id=2qjl22w` in the example output above), point the next run at it, and Loops reuses the same trainer and sampler:

```bash theme={"system"}
export LOOPS_REUSE_FROM_SESSION_ID=2qjl22w
uv run python train_loops.py
```

You can also pass the ID directly in code, which wins if both the kwarg and the environment variable are set:

```python theme={"system"}
service_client = tinker.ServiceClient(reuse_from_session_id="2qjl22w")
```

From the HTTP API, send `reuse_from_session_id` in the body of [`POST /v1/loops/runs`](/reference/loops-api/runs/create-a-run) or [`POST /v1/loops/samplers`](/reference/loops-api/samplers/create-a-sampler).

Reuse is best-effort. If the prior trainer is stopped, failed, or unhealthy, Loops provisions a fresh one and your script still runs.

## Shut down the session

You're billed for the trainer and sampler's GPUs until you deactivate them. When you're done experimenting, check what's live and shut it down:

```bash theme={"system"}
uvx truss loops view
uvx truss loops deactivate <deployment_id> --yes
```

[`truss loops view`](/reference/cli/loops/loops-cli#view) lists the deployments that are still running, with the ID, base model, and status of each. Pass the `Deployment ID` to [`deactivate`](/reference/cli/loops/loops-cli#deactivate). Your checkpoints survive the shutdown: you can still list them, fetch their files, and deploy them to inference afterward.

## Next steps

* **Deploy the checkpoint to inference**: Run [`truss loops checkpoints deploy --checkpoint-ids <id>`](/reference/cli/loops/loops-cli#checkpoints-deploy) and answer the prompts for model name, GPU, and Hugging Face secret. Deploying needs an `hf_access_token` in [workspace secrets](/organization/secrets) because the deployment downloads the base weights from Hugging Face. Call the result at `https://model-<model_id>.api.baseten.co/deployment/<deployment_id>/sync/v1/chat/completions` with `"model"` set to the checkpoint name (here, `step-1`).
* **[Loops concepts](/loops/concepts)**: Sessions, trainers, samplers, checkpoints, and how weight sync works.
* **[Tinker compatibility](/loops/tinker-compatibility)**: What carries over from Tinker unchanged and what differs: checkpoint layout, authentication, and cluster routing.
* **[Loops API reference](/reference/loops-api/overview)**: Every HTTP route, for scripting deployments and CI pipelines.
