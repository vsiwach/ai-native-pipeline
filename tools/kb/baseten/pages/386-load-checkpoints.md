# Load checkpoints
Source: https://docs.baseten.co/training/loading

Resume training from existing checkpoints to continue where you left off.

Checkpoint loading lets you resume training from previously saved model states. When enabled, Baseten automatically downloads your specified checkpoints to the training environment before your training code starts.

**Use cases:**

* Resume failed training jobs.
* Incremental training and fine-tuning.

## Access downloaded checkpoints

Checkpoints are available through the `BT_LOAD_CHECKPOINT_DIR` environment variable. For single-node training, they're located in `BT_LOAD_CHECKPOINT_DIR/rank-0/`. For multi-node training, each node's checkpoints are in `BT_LOAD_CHECKPOINT_DIR/rank-<node_rank>/`.

## Checkpoint reference

Create references to checkpoints using the `BasetenCheckpoint` factory:

### From latest

```python theme={"system"}
# Load the latest checkpoint from a project
BasetenCheckpoint.from_latest_checkpoint(project_name="my-training-project")

# Load the latest checkpoint from a previous job
BasetenCheckpoint.from_latest_checkpoint(job_id="gvpql31")
```

**Parameters:**

* `project_name`: Load the latest checkpoint from the most recent job in this project.
* `job_id`: Load the latest checkpoint from this specific job.
* Both parameters: Load the latest checkpoint from that specific job in that project.

### From named

```python theme={"system"}
# Pin your starting point to a specific checkpoint
BasetenCheckpoint.from_named_checkpoint(checkpoint_name="checkpoint-20", job_id="gvpql31")
```

**Parameters:**

* `checkpoint_name`: The name of the specific checkpoint to load.
* `job_id`: The job that contains the named checkpoint.
* Both parameters: Load the named checkpoint from that specific job in that project.

## Configuration examples

Here are practical examples of how to configure checkpoint loading in your training jobs:

### From latest

```python theme={"system"}
# Latest checkpoint from project
load_config = LoadCheckpointConfig(
    enabled=True,
    checkpoints=[
        BasetenCheckpoint.from_latest_checkpoint(project_name="gpt-finetuning")
    ]
)

# Latest checkpoint from specific job
load_config = LoadCheckpointConfig(
    enabled=True,
    checkpoints=[
        BasetenCheckpoint.from_latest_checkpoint(job_id="gvpql31")
    ]
)
```

### From named

```python theme={"system"}
# Specific named checkpoint
load_config = LoadCheckpointConfig(
    enabled=True,
    checkpoints=[
        BasetenCheckpoint.from_named_checkpoint(
            checkpoint_name="checkpoint-20",
            job_id="gvpql31"
        )
    ]
)

# Named checkpoint with custom download location
load_config = LoadCheckpointConfig(
    enabled=True,
    download_folder="/tmp/my_checkpoints",
    checkpoints=[
        BasetenCheckpoint.from_named_checkpoint(
            checkpoint_name="checkpoint-20",
            job_id="rwnojdq"
        )
    ]
)
```

**Configuration parameters:**

* `enabled`: Set to `True` to enable checkpoint loading.
* `checkpoints`: List containing checkpoint references.
* `download_folder`: Optional custom download location (defaults to `/tmp/loaded_checkpoints`).

## Complete TrainingJob setup

```python theme={"system"}
from truss_train import LoadCheckpointConfig, BasetenCheckpoint, CheckpointingConfig, TrainingJob, Image, Runtime, TrainingProject
from truss_train.definitions import CacheConfig

# Configure checkpoint loading
load_checkpoint_config = LoadCheckpointConfig(
    enabled=True,
    download_folder="/tmp/loaded_checkpoints",
    checkpoints=[
        BasetenCheckpoint.from_latest_checkpoint(job_id="previous_job_id")
    ]
)

# Configure checkpointing for saving new checkpoints
checkpointing_config = CheckpointingConfig(
    enabled=True,
    checkpoint_path="/tmp/training_checkpoints"
)

# Create TrainingJob
job = TrainingJob(
    image=Image(base_image="your-base-image"),
    runtime=Runtime(
        checkpointing_config=checkpointing_config,
        load_checkpoint_config=load_checkpoint_config,
        start_commands=["chmod +x ./run.sh && ./run.sh"],
        cache_config=CacheConfig(enabled=True)
    ),
)

project = TrainingProject(name="my-training-project", job=job)
```

## Use checkpoints in your training code

Access loaded checkpoints using the `BT_LOAD_CHECKPOINT_DIR` environment variable:

```python theme={"system"}
from transformers import AutoModelForSequenceClassification, AutoTokenizer, TrainingArguments, Trainer
from transformers.trainer_utils import get_last_checkpoint
import os

def train():
    checkpoint_dir = os.environ.get("BT_LOAD_CHECKPOINT_DIR")
    last_checkpoint = None

    if checkpoint_dir:
        last_checkpoint = get_last_checkpoint(checkpoint_dir)
        if last_checkpoint:
            print(f"✅ Resuming from checkpoint: {last_checkpoint}")
            model = AutoModelForSequenceClassification.from_pretrained(last_checkpoint)
            tokenizer = AutoTokenizer.from_pretrained(checkpoint_dir)
        else:
            print("⚠️ No checkpoint found, starting from scratch")
            model = AutoModelForSequenceClassification.from_pretrained("your-base-model")
            tokenizer = AutoTokenizer.from_pretrained("your-base-model")
    else:
        print("ℹ️ No checkpoint loading configured")
        model = AutoModelForSequenceClassification.from_pretrained("your-base-model")
        tokenizer = AutoTokenizer.from_pretrained("your-base-model")

    training_args = TrainingArguments(
        output_dir=os.environ.get("BT_CHECKPOINT_DIR", "/tmp/training_checkpoints"),
        save_strategy="steps",
        save_steps=1000,
        load_best_model_at_end=True,
    )

    trainer = Trainer(model=model, args=training_args)
    trainer.train(resume_from_checkpoint=last_checkpoint)
```
