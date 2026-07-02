# Get started
Source: https://docs.baseten.co/training/getting-started

Run your first training job and deploy it to production.

Baseten Training runs your training code on managed cloud GPUs. You bring your
own framework, point it at a GPU type, and submit. Baseten handles provisioning,
syncs checkpoints as they're saved, and deploys any checkpoint as a production
endpoint in one command.

This tutorial fine-tunes Qwen3-4B with LoRA on a single H100, from job
submission to calling the deployed model.

You'll set up a project directory, define your infrastructure in a configuration file, and write the training scripts that run on an H100.

You're billed per minute of GPU time while the job runs and while the deployed model serves traffic; see [Baseten pricing](https://www.baseten.co/pricing/) for H100 rates. The training job is capped at 50 steps, so it ends on its own.

## Prerequisites

* **Baseten account**: [Sign up for Baseten](https://app.baseten.co/).
* **API key**: Generate an API key from [Settings > API keys](https://app.baseten.co/settings/account/api_keys).
* **Hugging Face token**: Store a [Hugging Face access token](https://huggingface.co/settings/tokens) as a [Baseten secret](/organization/secrets) named `hf_access_token`. The deploy step at the end of this tutorial needs it to download the base model.
* **[uv](https://docs.astral.sh/uv/)**: This guide uses `uvx` to run [Truss](https://pypi.org/project/truss/) commands without a separate install step. Log in to Baseten:

  ```bash theme={"system"}
  uvx truss login
  ```

## Create your training project

```bash theme={"system"}
mkdir my-training-project && cd my-training-project
```

### Write your configuration file

Your configuration file uses the `truss_train` library to define your training
infrastructure as Python objects:

* [`TrainingProject`](/reference/sdk/training#trainingproject): the top-level container for your project.
* [`TrainingJob`](/reference/sdk/training#trainingjob): a single job within a project, combining:
  * [`Image`](/reference/sdk/training#image): what container to run.
  * [`Compute`](/reference/sdk/training#compute): what hardware to provision.
  * [`Runtime`](/reference/sdk/training#runtime): how to start training and what to persist.

This is the file Baseten reads when you submit a job. It tells the platform
which GPU to provision, which container image to use, and where to sync
checkpoints.

Create `config.py`:

```python config.py theme={"system"}
from truss_train import (
    TrainingProject,
    TrainingJob,
    Image,
    Compute,
    Runtime,
    CacheConfig,
    CheckpointingConfig,
)
from truss.base.truss_config import AcceleratorSpec

BASE_IMAGE = "pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime"

training_runtime = Runtime(
    start_commands=[
        "chmod +x ./run.sh && ./run.sh",
    ],
    cache_config=CacheConfig(enabled=True),
    checkpointing_config=CheckpointingConfig(enabled=True),
)

training_compute = Compute(
    accelerator=AcceleratorSpec(accelerator="H100", count=1),
)

training_job = TrainingJob(
    image=Image(base_image=BASE_IMAGE),
    compute=training_compute,
    runtime=training_runtime,
)

training_project = TrainingProject(
    name="qwen3-4b-lora-sft",
    job=training_job,
)
```

`CacheConfig` avoids re-downloading models and datasets between jobs.
`CheckpointingConfig` tells Baseten to sync your saved checkpoints so you can
deploy them later.

### Write your training scripts

Create `run.sh` to install dependencies and launch training. This tutorial uses
`pip install` in the start command, but you can also pre-install dependencies in
a [custom base image](/training/concepts/basics#base-images).

```bash run.sh theme={"system"}
#!/bin/bash
set -eux

pip install "trl>=0.20.0" "peft>=0.17.0" "transformers>=4.55.0" "datasets"

python train.py
```

Your `train.py` is your own training code. Baseten runs it as-is, so you can use
any framework or training loop that works locally. This example fine-tunes
[Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B) on the
[pirate-ultrachat-10k](https://huggingface.co/datasets/winglian/pirate-ultrachat-10k)
dataset using LoRA with [TRL](https://huggingface.co/docs/trl) (Transformer
Reinforcement Learning). The dataset teaches the model to respond in pirate
dialect, so you'll know fine-tuning worked when the deployed model starts saying
"Ahoy, matey!"

```python train.py theme={"system"}
import os
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer

MODEL_ID = "Qwen/Qwen3-4B"
DATASET_ID = "winglian/pirate-ultrachat-10k"

dataset = load_dataset(DATASET_ID, split="train")

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    use_cache=False,
)

peft_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules="all-linear",
    lora_dropout=0.05,
    task_type="CAUSAL_LM",
)

training_args = SFTConfig(
    learning_rate=2e-4,
    num_train_epochs=1,
    max_steps=50,
    logging_steps=5,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    gradient_checkpointing=True,
    max_length=1024,
    warmup_ratio=0.1,
    lr_scheduler_type="cosine",
    save_steps=25,
    bf16=True,
    output_dir=os.getenv("BT_CHECKPOINT_DIR", "./checkpoints"),
)

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
    processing_class=tokenizer,
    peft_config=peft_config,
)
trainer.train()

trainer.save_model(training_args.output_dir)
print(f"Training complete. Model saved to {training_args.output_dir}")
```

<Note>
  Save checkpoints to `$BT_CHECKPOINT_DIR` so Baseten can sync and deploy them.
  Baseten sets this variable automatically when checkpointing is enabled.
</Note>

With `save_steps=25` and `max_steps=50`, the trainer saves LoRA checkpoints at
steps 25 and 50.

## Submit your training job

Now that your project is set up, submit your training job. The CLI packages your
files, creates the training project, and starts the job on your specified GPU.

```bash theme={"system"}
uvx truss train push config.py
```

You'll see:

```output theme={"system"}
✨ Training job successfully created!
🪵 View logs for your job via 'truss train logs --job-id <job_id> --tail'
🔍 View metrics for your job via 'truss train metrics --job-id <job_id>'
🌐 View job in the UI: https://app.baseten.co/training/<project_id>/logs/<job_id>
```

Copy the `job_id` to use in the next steps.

## Monitor your training job

Tail logs in real time with the job ID from the previous step.

```bash theme={"system"}
uvx truss train logs --job-id <job_id> --tail
```

You can also view logs, metrics, and job status in the [Baseten dashboard](https://app.baseten.co/training/).

## Deploy your trained model

When training finishes, Baseten syncs your checkpoints automatically. You'll see:

```output theme={"system"}
Training complete. Model saved to /mnt/ckpts
Job has exited. Syncing checkpoints...
```

<Tabs>
  <Tab title="CLI">
    Deploy your checkpoint to Baseten's inference platform. The deployment downloads
    the base model weights and serves them with your LoRA adapter using vLLM. This
    step uses the `hf_access_token` secret from the prerequisites because the
    serving layer downloads the base model separately.

    ```bash theme={"system"}
    uvx truss train deploy_checkpoints
    ```

    Follow the interactive prompts to select a checkpoint, name your model, and choose a GPU.

    ```output theme={"system"}
    Fetching checkpoints for training job <job_id>...
    ? Use spacebar to select/deselect checkpoints to deploy.
      ○ .
      ○ checkpoint-50
    ❯ ○ checkpoint-25

    ? Enter the model name for your deployment: my-fine-tuned-model
    ? Select the GPU type to use for deployment: H100
    ? Select the number of H100 GPUs to use for deployment: 1
    ? Enter the huggingface secret name: hf_access_token

    Successfully created model version: deployment-1
    Model version ID: <model_version_id>
    ```
  </Tab>

  <Tab title="Dashboard">
    Deploy from the [Baseten dashboard](https://app.baseten.co/training/):

    1. Select your training job.
    2. Open the **Checkpoints** tab and choose a checkpoint.
    3. Click **Deploy** and configure your model name, instance type, and scaling settings.
  </Tab>
</Tabs>

### Test your deployment

Call your deployed model using the OpenAI-compatible chat format. The `model` field matches the checkpoint name you selected during deployment.

<Tabs>
  <Tab title="cURL">
    ```bash theme={"system"}
    export BASETEN_API_KEY="paste-your-api-key-here"

    curl -X POST https://model-<id>.api.baseten.co/v1/chat/completions \
      -H "Authorization: Bearer $BASETEN_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"model": "checkpoint-25", "messages": [{"role": "user", "content": "What is the best way to learn Python programming?"}]}'
    ```
  </Tab>

  <Tab title="Python">
    ```python theme={"system"}
    import os
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["BASETEN_API_KEY"],
        base_url="https://model-<model_id>.api.baseten.co/environments/production/sync/v1"
    )

    response = client.chat.completions.create(
        model="checkpoint-25",
        messages=[{"role": "user", "content": "What is the best way to learn Python programming?"}],
    )

    print(response.choices[0].message.content)
    ```
  </Tab>

  <Tab title="CLI">
    ```bash theme={"system"}
    uvx truss predict --model <model-id> --data '{"model": "checkpoint-25", "messages": [{"role": "user", "content": "What is the best way to learn Python programming?"}]}'
    ```
  </Tab>
</Tabs>

The fine-tuned model responds in pirate dialect, confirming that the LoRA adapter is active:

```output theme={"system"}
Ahoy there matey! Seeking knowledge of Python programming? Well, it's a
treasure trove, but it takes patience and practice to find the gold...
```

## Next steps

* [Monitor and manage training jobs](/training/management): for logs, metrics, and job lifecycle commands.
* [Training SDK reference](/reference/sdk/training): for all configuration options, including [base images](/reference/sdk/training#image), [secrets](/reference/sdk/training#secretreference), [private registries](/reference/sdk/training#dockerauth), and [`.truss_ignore` syntax](/reference/cli/training/training-cli#ignoring-files-and-folders).
* Browse the [ML Cookbook](https://github.com/basetenlabs/ml-cookbook): for framework examples and [advanced recipes](https://github.com/basetenlabs/ml-cookbook/tree/main/recipes).
