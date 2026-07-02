# Lifecycle
Source: https://docs.baseten.co/training/lifecycle

Understanding the different states and transitions in a Baseten training job's lifecycle.

A training job in Baseten progresses through several states from creation to completion. Understanding these states helps you monitor and manage your training jobs effectively.

## Job states

| State                        | Description                                                                                                                                      | Active | Terminal |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------ | -------- |
| `TRAINING_JOB_PENDING`       | The job is queued, waiting for GPU capacity to free up. [Queue priority](/training/management#queue-priority) sets the order among pending jobs. | ✅      |          |
| `TRAINING_JOB_CREATED`       | Initial state when a job is first created. Baseten has received the training configuration and persisted it to our records.                      | ✅      |          |
| `TRAINING_JOB_DEPLOYING`     | Baseten is deploying the job, including provisioning compute resources and installing dependencies.                                              | ✅      |          |
| `TRAINING_JOB_RUNNING`       | The training code is actively executing.                                                                                                         | ✅      |          |
| `TRAINING_JOB_COMPLETED`     | The job has successfully finished execution. Any checkpoints or artifacts have been saved and uploaded.                                          |        | ✅        |
| `TRAINING_JOB_DEPLOY_FAILED` | The job failed to deploy. This is likely due to a bad image or a resource allocation issue.                                                      |        | ✅        |
| `TRAINING_JOB_FAILED`        | The job encountered an error and could not complete successfully. Check the logs for error details.                                              |        | ✅        |
| `TRAINING_JOB_STOPPED`       | The job was manually stopped by a user.                                                                                                          |        | ✅        |

## State transitions

Jobs typically progress through states in the following order:

1. `TRAINING_JOB_PENDING` → `TRAINING_JOB_CREATED`: Automatic transition once GPU capacity is available
2. `TRAINING_JOB_CREATED` → `TRAINING_JOB_DEPLOYING`: Automatic transition once resources are allocated
3. `TRAINING_JOB_DEPLOYING` → `TRAINING_JOB_RUNNING`: Automatic transition once environment setup is complete
4. `TRAINING_JOB_RUNNING` → `TRAINING_JOB_COMPLETED`: Automatic transition upon successful completion

A job may enter `TRAINING_JOB_FAILED` from any state if an error occurs. Similarly, `TRAINING_JOB_STOPPED` can be entered from any active state (`PENDING`, `DEPLOYING`, or `RUNNING`) when manually stopped.

You can monitor these state transitions using the CLI command:

```bash theme={"system"}
truss train view # shows all active jobs
truss train view --job-id <your_job_id> # shows a specific job
```

Or track a specific job's progress with:

```bash theme={"system"}
truss train logs --job-id <your_job_id> --tail
```
