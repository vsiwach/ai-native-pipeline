# Management
Source: https://docs.baseten.co/training/management

How to monitor, manage, and interact with your Baseten Training projects and jobs.

Once you've submitted training jobs, Baseten provides tools to manage your `TrainingProject`s and individual `TrainingJob`s. You can use the [CLI](/reference/cli/training/training-cli) or the [API](/reference/training-api/overview) to manage your jobs.

## `TrainingProject` management

* **Listing Projects:** To view all your training projects:
  ```bash theme={"system"}
  truss train view
  ```
  This command will list all `TrainingProject`s you have access to, typically showing their names and IDs. Additionally, this command will show all active jobs.

* **Viewing Jobs within a Project:** To see all jobs associated with a specific project, use its `project` (obtained when creating the project or from `truss train view`):
  ```bash theme={"system"}
  truss train view --project <project_id or project_name>
  ```

* **Deleting a `TrainingProject`:** You can delete a training project through the API, or through the dashboard.

  Using the API:

  ```bash theme={"system"}
  curl -X DELETE https://api.baseten.co/v1/training_projects/<training_project_id> \
    -H "Authorization: Bearer YOUR_API_KEY"
  ```

  From the Baseten dashboard:

  1. Select the training project you want to delete.
  2. Type the project name (for example, `demo/qwen3-0.6b`) to confirm.
  3. Select **Delete**.

  <Warning>
    When you delete a project, the following data is permanently deleted with no archival or recovery option:

    * All undeployed [checkpoints](/training/concepts/checkpoints) from every job in the project
    * All data in the project's [training cache](/training/concepts/cache) (`$BT_PROJECT_CACHE_DIR`)

    Checkpoints that have been [deployed](/training/deployment) aren't affected.
  </Warning>

## `TrainingJob` management

After submitting a job with `truss train push config.py`, you receive a `project_id` and `job_id`.

* **Listing Jobs:** As shown above, you can list all jobs within a project using:
  ```bash theme={"system"}
  truss train view --project <project_id or project_name>
  ```
  This will typically show job IDs, statuses, creation times, etc.

* **Checking Status and Retrieving Logs:** To view the logs for a specific job, you can tail them in real-time or fetch existing logs.
  * To view logs for the most recently submitted job in the current context (for example, if you just pushed a job from your current terminal directory):
    ```bash theme={"system"}
    truss train logs --tail
    ```
  * To view logs for a specific job using its `job-id`:
    ```bash theme={"system"}
    truss train logs --job-id <your_job_id> [--tail]
    ```
    Add `--tail` to follow the logs live.

* **Understanding Job Statuses:**
  The `truss train view` and `truss train logs` commands will help you track which status a job is in. For more on the job lifecycle, see the [Lifecycle](/training/lifecycle) page.

* **Stopping a `TrainingJob`:** If you need to stop a running or pending job, use the `stop` command with the job's project ID and job ID:
  ```bash theme={"system"}
  truss train stop --job-id <your_job_id>
  truss train stop --all # Stops all active jobs; Will prompt the user for confirmation.
  ```
  This will transition the job to the `TRAINING_JOB_STOPPED` state.

* **Deleting a `TrainingJob`:** You can delete a training job through the API, or through the dashboard.

  Using the API:

  ```bash theme={"system"}
  curl -X DELETE https://api.baseten.co/v1/training_projects/<training_project_id>/jobs/<training_job_id> \
    -H "Authorization: Bearer YOUR_API_KEY"
  ```

  From the Baseten dashboard:

  1. Select the project containing the job.
  2. Select the job you want to delete.
  3. Type the job name (for example, `job-2`) to confirm.
  4. Select **Delete**.

  <Warning>
    When you delete a job, all undeployed checkpoints are deleted permanently. There's no archival or recovery option. Checkpoints that have been [deployed](/training/deployment) aren't affected.
  </Warning>

* **Understanding Job Outputs & Checkpoints:**
  * The primary outputs of a successful `TrainingJob` are model **checkpoints** (if checkpointing is enabled and configured).
  * These checkpoints are stored by Baseten. For more information on how `CheckpointingConfig` works, see [Checkpoints](/training/concepts/checkpoints).
  * When you are ready to [deploy a model](/training/deployment), you will specify which checkpoints to use. The `model_name` you assign during deployment (using `DeployCheckpointsConfig`) becomes the identifier for this trained model version derived from your specific job's checkpoints.
  * You can see the available checkpoints for a job through the [Training API](/reference/training-api/get-training-job-checkpoints).

## Queue priority

When GPU capacity is full, new training jobs wait in a queue (the [`TRAINING_JOB_PENDING`](/training/lifecycle) state). Set `--priority` on `truss train push` to control the order jobs leave that queue:

```bash theme={"system"}
truss train push config.py --priority 100
```

Higher values run first. Jobs default to priority `0`. Raise a job above `0` to run it sooner, or drop it below `0` to hold it behind default-priority work; the value is an unbounded integer.

Priority only reorders jobs that are waiting for capacity. It doesn't pause a running job or add capacity, so raising priority helps only when jobs are queued and capacity frees up.

Set priority when you submit the job. To change a pending job's priority, stop it with `truss train stop` and resubmit at the new value.
