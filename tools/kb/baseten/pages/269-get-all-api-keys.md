# Get all API keys
Source: https://docs.baseten.co/reference/management-api/api-keys/lists-the-users-api-keys

get /v1/api_keys
Lists all API keys your account has access to.

<ResponseExample>
  ```json 200 theme={"system"}
  {
    "name": "my-api-key", 
    "type": "PERSONAL"
  }
  ```
</ResponseExample>
