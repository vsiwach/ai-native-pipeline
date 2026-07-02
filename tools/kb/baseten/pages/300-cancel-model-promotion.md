# Cancel model promotion
Source: https://docs.baseten.co/reference/management-api/deployments/promote/cancel-promotion

post /v1/models/{model_id}/environments/{env_name}/cancel_promotion
Cancels an ongoing promotion to an environment and returns the cancellation status.

<ResponseExample>
  ```json 200 theme={"system"}
  {
    "status": "CANCELED",
    "message": "Promotion to production was successfully canceled."
  }
  ```

  ```json 400 theme={"system"}
  {
    "code": "VALIDATION_ERROR",
    "message": "Environment production has no in progress promotion."
  }
  ```
</ResponseExample>
