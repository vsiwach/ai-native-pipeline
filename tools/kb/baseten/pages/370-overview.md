# Overview
Source: https://docs.baseten.co/reference/training-api/overview

Programmatically manage Baseten Training resources.

The Training API manages training projects, jobs, and related resources through a RESTful interface. Use this API to:

* Monitor training job metrics and logs
* Manage training jobs
* Manage checkpoints and artifacts

## Authentication

All Training API requests require authentication with an API key:

```bash theme={"system"}
Authorization: Bearer EMPTY
```

## Base URL

All Training API endpoints are relative to:

```text theme={"system"}
https://api.baseten.co/v1
```

## Available Endpoints

### Training Projects

| Method   | Endpoint                                                                                                               | Description                        |
| -------- | ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| `GET`    | [`/training_projects`](/reference/training-api/get-training-projects)                                                  | List all training projects         |
| `GET`    | [`/training_projects/{training_project_id}`](/reference/training-api/get-training-project)                             | Get a training project             |
| `POST`   | [`/training_projects`](/reference/training-api/create-training-project)                                                | Create a training project          |
| `DELETE` | [`/training_projects/{training_project_id}`](/reference/training-api/delete-training-project)                          | Delete a training project          |
| `GET`    | [`/training_projects/{training_project_id}/cache/summary`](/reference/training-api/get-training-project-cache-summary) | Get training project cache summary |

### Training Jobs

The following endpoints use the relative base path: `/training_projects/{training_project_id}/jobs`

| Method   | Endpoint                                                                                              | Description                       |
| -------- | ----------------------------------------------------------------------------------------------------- | --------------------------------- |
| `POST`   | [`.../`](/reference/training-api/create-training-job)                                                 | Create a training job             |
| `GET`    | [`.../`](/reference/training-api/list-training-jobs)                                                  | List all jobs in a project        |
| `GET`    | [`.../{training_job_id}`](/reference/training-api/get-training-job)                                   | Get a specific training job       |
| `POST`   | [`.../{training_job_id}/stop`](/reference/training-api/stop-training-job)                             | Stop a training job               |
| `DELETE` | [`.../{training_job_id}`](/reference/training-api/delete-training-job)                                | Delete a training job             |
| `POST`   | [`.../{training_job_id}/recreate`](/reference/training-api/recreate-training-job)                     | Recreate a training job           |
| `GET`    | [`.../{training_job_id}/logs`](/reference/training-api/get-training-job-logs)                         | Get training job logs             |
| `GET`    | [`.../{training_job_id}/metrics`](/reference/training-api/get-training-job-metrics)                   | Get training job metrics          |
| `GET`    | [`.../{training_job_id}/checkpoints`](/reference/training-api/get-training-job-checkpoints)           | List job checkpoints              |
| `GET`    | [`.../{training_job_id}/checkpoint_files`](/reference/training-api/get-training-job-checkpoint-files) | Get training job checkpoint files |
| `GET`    | [`.../{training_job_id}/download`](/reference/training-api/download-training-job)                     | Download training job artifacts   |
| `GET`    | [`.../{training_job_id}/auth_codes`](/reference/training-api/get-auth-codes-for-training-job)         | Get auth codes for a training job |

Search endpoint:

| Method | Endpoint                                                                | Description                     |
| ------ | ----------------------------------------------------------------------- | ------------------------------- |
| `POST` | [`/training_jobs/search`](/reference/training-api/search-training-jobs) | Search across all training jobs |
