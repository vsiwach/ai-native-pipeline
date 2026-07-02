# Create a model with the REST API
Source: https://docs.baseten.co/examples/create-a-model-with-rest

Deploy a model archive programmatically using the management API, without the Truss CLI.

The management API deploys a model from a Truss archive over REST, the same deployment you'd get from [`truss push`](/reference/cli/truss/push) but without a Python dependency. Use it from a service or CI pipeline that can't run the Python Truss CLI, such as a Go or JavaScript backend. If you're already working in Python, `truss push` is the simpler path.

Deploying over REST follows the same path each time:

1. **Prepare**: [`POST /v1/prepare_model_upload`](/reference/management-api/models/prepare-model-upload) validates the payload and returns temporary credentials scoped to an S3 location.
2. **Upload**: push your Truss archive to that location.
3. **Create**: [`POST /v1/models`](/reference/management-api/models/creates-a-model-from-a-source) commits the upload as a new model.

## Prepare the upload

Send a Truss config as a JSON object with a model `name`. Add a [`weights` block](/development/model/bdn#weights) to load weights through the Baseten Delivery Network. Set `dry_run` to `true` to validate without issuing credentials. The response carries the upload credentials and the S3 location to upload to:

<CodeGroup>
  ```bash Request theme={"system"}
  curl https://api.baseten.co/v1/prepare_model_upload \
    -H "Authorization: Bearer $BASETEN_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "name": "my-model",
      "deployment": {
        "config": { "model_name": "my-model", "resources": { "accelerator": "A10G" }, "weights": [{ "source": "hf://meta-llama/Llama-3.1-8B@main", "mount_location": "/models/llama" }] }
      }
    }'
  ```

  ```json 200 theme={"system"}
  {
    "creds": {
      "aws_access_key_id": "ASIA...",
      "aws_secret_access_key": "...",
      "aws_session_token": "..."
    },
    "s3_bucket": "baseten-user-models-xxxx",
    "s3_key": "organizations/.../models/.../model.tgz",
    "s3_region": "us-west-2"
  }
  ```
</CodeGroup>

## Upload the archive

Package your Truss as a gzipped tar archive, then upload it to the returned `s3_bucket` and `s3_key` using the temporary credentials:

```python upload.py theme={"system"}
import boto3

# resp is the JSON returned by the prepare step
creds = resp["creds"]
session = boto3.Session(
    aws_access_key_id=creds["aws_access_key_id"],
    aws_secret_access_key=creds["aws_secret_access_key"],
    aws_session_token=creds["aws_session_token"],
    region_name=resp["s3_region"],
)
session.client("s3").upload_file("model.tgz", resp["s3_bucket"], resp["s3_key"])
```

A successful upload returns nothing. `boto3` raises an exception if the temporary credentials have expired or the `s3_key` doesn't match the one from the prepare step.

## Create the model

Commit the upload with `source.kind` set to `model_archive`, the same `deployment` payload you validated, and the `s3_key` from the prepare step. The response returns the created model and its first deployment:

<CodeGroup>
  ```bash Request theme={"system"}
  curl https://api.baseten.co/v1/models \
    -H "Authorization: Bearer $BASETEN_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "source": {
        "kind": "model_archive",
        "name": "my-model",
        "s3_key": "organizations/.../models/.../model.tgz",
        "deployment": {
          "config": { "model_name": "my-model", "resources": { "accelerator": "A10G" }, "weights": [{ "source": "hf://meta-llama/Llama-3.1-8B@main", "mount_location": "/models/llama" }] }
        }
      }
    }'
  ```

  ```json 200 theme={"system"}
  {
    "model": { "id": "abcd123", "name": "my-model" },
    "deployment": { "id": "1q2w3e4", "status": "BUILDING" }
  }
  ```
</CodeGroup>

The deployment starts at `BUILDING` and isn't ready when the call returns. Poll [`GET /v1/models/{model_id}/deployments/{deployment_id}`](/reference/management-api/deployments/gets-a-models-deployment-by-id) until its `status` is `ACTIVE`:

<CodeGroup>
  ```bash Request theme={"system"}
  curl https://api.baseten.co/v1/models/abcd123/deployments/1q2w3e4 \
    -H "Authorization: Bearer $BASETEN_API_KEY"
  ```

  ```json 200 theme={"system"}
  {
    "id": "1q2w3e4",
    "model_id": "abcd123",
    "status": "ACTIVE",
    "environment": "production",
    "active_replica_count": 1
  }
  ```
</CodeGroup>

## Call the model

Once the deployment is `ACTIVE`, send inference requests to the model's predict endpoint, using the model `id` from the create response and your API key. The request and response shapes match whatever your model's `predict` method accepts and returns:

<CodeGroup>
  ```bash Request theme={"system"}
  curl https://model-abcd123.api.baseten.co/environments/production/predict \
    -H "Authorization: Bearer $BASETEN_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Hello!"}'
  ```

  ```json 200 theme={"system"}
  { "output": "Hello! How can I help you today?" }
  ```
</CodeGroup>

## Next steps

<CardGroup>
  <Card title="Call your model" icon="paper-plane" href="/inference/calling-your-model">
    Stream responses, send async requests, and use the other inference transports.
  </Card>

  <Card title="Add a deployment" icon="layer-group" href="/reference/management-api/deployments/adds-a-deployment-to-a-model">
    Push a new deployment to the model you created.
  </Card>
</CardGroup>
