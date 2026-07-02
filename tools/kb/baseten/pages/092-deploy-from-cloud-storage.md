# Deploy from cloud storage
Source: https://docs.baseten.co/engines/performance-concepts/cloud-storage-deployment

Connect your S3 bucket, GCS bucket, Azure container, or Hugging Face repository to Baseten's TRT-LLM inference engines and deploy without re-uploading weights.

Deploying from cloud storage lets you use your existing infrastructure. The engine pulls weights from your storage at build time, compiles them with TensorRT-LLM, and serves the result as a production endpoint. You don't need to move or re-upload anything.

[Engine-Builder-LLM](/engines/engine-builder-llm/overview), [BEI](/engines/bei/overview), and [BIS-LLM](/engines/bis-llm/overview) all support this workflow.

<Note>
  To deploy from Baseten Training checkpoints instead, see [Deploy with optimized inference engines](/training/deploy-with-engine-builder).
</Note>

## Storage sources

The `checkpoint_repository` field in your config specifies where the engine pulls weights from. The `source` field accepts the following providers:

* `S3`: Amazon S3 buckets.
* `GCS`: Google Cloud Storage.
* `AZURE`: Azure Blob Storage.
* `HF`: Hugging Face repositories.

The `revision` field pins a specific commit or branch. For Hugging Face repos, this is a git ref (branch name, tag, or commit SHA). If unset, the engine uses the default branch. For cloud storage sources (S3, GCS, Azure), `revision` is not applicable. The repo path points to a specific prefix.

Here's a minimal example using S3:

```yaml config.yaml theme={"system"}
trt_llm:
  build:
    base_model: decoder
    checkpoint_repository:
      source: S3  # or GCS, AZURE, HF
      repo: s3://your-bucket/path/to/model/
```

## Private storage credentials

To access private storage, add a JSON secret to your [Baseten secrets manager](https://app.baseten.co/settings/secrets) and reference it with `runtime_secret_name` in your config.

<Tabs>
  <Tab title="S3">
    Add a secret with your AWS credentials:

    ```json theme={"system"}
    {
      "aws_access_key_id": "XXXXX",
      "aws_secret_access_key": "xxxxx/xxxxxx",
      "aws_region": "us-west-2"
    }
    ```

    Then reference the secret in your config:

    ```yaml config.yaml theme={"system"}
    secrets:
      aws_secret_json: "set token in baseten workspace"
    trt_llm:
      build:
        checkpoint_repository:
          source: S3
          repo: s3://your-bucket/path/to/model
          runtime_secret_name: aws_secret_json
    ```

    See [AWS S3 authentication](/development/model/bdn#aws-s3) for full setup details including OIDC.
  </Tab>

  <Tab title="GCS">
    Add a secret with your GCP service account credentials:

    ```json theme={"system"}
    {
      "private_key_id": "xxxxxxx",
      "private_key": "-----BEGIN PRIVATE KEY-----\nMI",
      "client_email": "b10-some@xxx-example.iam.gserviceaccount.com"
    }
    ```

    Then reference the secret in your config:

    ```yaml config.yaml theme={"system"}
    secrets:
      gcp_service_account: "set token in baseten workspace"
    trt_llm:
      build:
        checkpoint_repository:
          source: GCS
          repo: gs://your-bucket/path/to/model
          runtime_secret_name: gcp_service_account
    ```

    See [Google Cloud Storage authentication](/development/model/bdn#google-cloud-storage) for full setup details including GCP OIDC.
  </Tab>

  <Tab title="Azure">
    Add a secret with your Azure account key:

    ```json theme={"system"}
    {
      "account_key": "xxxxx"
    }
    ```

    Then reference the secret in your config:

    ```yaml config.yaml theme={"system"}
    secrets:
      azure_secret_json: "set token in baseten workspace"
    trt_llm:
      build:
        checkpoint_repository:
          source: AZURE
          repo: az://your-container/path/to/model
          runtime_secret_name: azure_secret_json
    ```
  </Tab>

  <Tab title="Hugging Face">
    Public repositories don't require a secret. For private or gated repositories, add your Hugging Face API token as a plain-text secret, then reference it in your config:

    ```yaml config.yaml theme={"system"}
    secrets:
      hf_access_token: "set token in baseten workspace"
    trt_llm:
      build:
        checkpoint_repository:
          source: HF
          repo: meta-llama/Llama-3.1-8B
          runtime_secret_name: hf_access_token
    ```

    Get your token from [Hugging Face settings](https://huggingface.co/settings/tokens). The `runtime_secret_name` field defaults to `hf_access_token`, so you can omit it for public repos.
  </Tab>
</Tabs>

## Related

* [Configure Engine-Builder-LLM deployments](/engines/engine-builder-llm/engine-builder-config): Complete build and runtime options for LLMs.
* [Configure BEI deployments](/engines/bei/bei-reference): Complete configuration for encoder models.
* [Set up cloud storage authentication](/development/model/bdn): OIDC and service account authentication for cloud storage.
* [Manage deployment secrets](/development/model/secrets): Configure credentials for private storage.
