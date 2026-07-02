# Baseten Delivery Network
Source: https://docs.baseten.co/development/model/bdn

Optimize cold starts with multi-tier caching and data delivery

<StaticDiagramEngine />

Baseten Delivery Network (BDN) reduces cold start times by mirroring your model weights to Baseten's infrastructure and caching them close to your replicas.

Instead of downloading hundreds of gigabytes from sources like Hugging Face, Amazon S3, or Google Cloud Storage on every scale-up, BDN mirrors weights once and serves them from multi-tier caches.
Configure BDN using the `weights` key in your config.
This works with both `Model` class deployments and [custom Docker images](/development/model/custom-server).

<CardGroup>
  <Card title="Get started" icon="rocket" href="#quick-start">
    Add weights to a new model
  </Card>

  <Card title="Custom servers" icon="docker" href="#custom-servers">
    Use with vLLM, SGLang, and more
  </Card>

  <Card title="Migrate" icon="arrow-right" href="#migration-from-model_cache">
    Move from `model_cache`
  </Card>
</CardGroup>

<Tip>
  BDN mirrors any [supported source](#source-types-and-authentication) the same way. If your weights are only on local disk, [bundle them with your Truss](/development/model/model-class#bundled-data) for small models, or push them to a private Hugging Face repository for large ones.
</Tip>

## Quick start

Add a `weights` section to your `config.yaml`. The example highlights it inside a complete config; expand to see the full file:

```yaml config.yaml expandable {5-12} theme={"system"}
model_name: qwen-3-8b
resources:
  accelerator: H100
  use_gpu: true
weights:
  - source: "hf://Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218"  # Pin a commit SHA for reproducible deploys
    mount_location: "/models/qwen"
    auth:
      auth_method: CUSTOM_SECRET
      auth_secret_name: "hf_access_token"  # Required for private or gated repos
    allow_patterns: ["*.safetensors", "*.json", "tokenizer.*"]
    ignore_patterns: ["*.md", "*.txt"]
```

* [`source`](#param-source): Where to fetch weights from. Supports [Hugging Face](#hugging-face), [Baseten Training](#baseten-training), [S3](#aws-s3), [GCS](#google-cloud-storage), and [R2](#cloudflare-r2).
* [`mount_location`](#param-mount-location): Absolute path where the weights appear in your container.
* [`auth`](#param-auth): Credentials for private or gated sources.
* [`allow_patterns`](#param-allow-patterns): Download only the files matching these patterns, to skip large files you don't need.
* [`ignore_patterns`](#param-ignore-patterns): Skip files matching these patterns, like docs or unused formats.

<Note>
  BDN authenticates private or gated repos through this per-source `auth` block, which is separate from the top-level [`secrets`](/development/model/secrets) config. A `secrets` entry alone does not authenticate weight mirroring. Create the secret (here, `hf_access_token` with your Hugging Face token) in your [workspace settings](https://app.baseten.co/settings/secrets), then reference it by name. Public sources need no `auth`.
</Note>

### Access weights in your model

When your model starts, weights are already downloaded and available at your `mount_location`.
The directory structure from the source is preserved:

```text theme={"system"}
/models/qwen/   # your mount_location
├── config.json
├── model-00001-of-00004.safetensors
├── model-00002-of-00004.safetensors
├── ...
├── model.safetensors.index.json
├── tokenizer.json
└── tokenizer_config.json
```

Load weights directly from this path in your `load()` method. No download code needed:

```python model.py theme={"system"}
from transformers import AutoModelForCausalLM

class Model:
    def load(self):
        # Weights are already available at mount_location
        self._model = AutoModelForCausalLM.from_pretrained(
            "/models/qwen",
            torch_dtype="auto",
            device_map="auto"
        )
```

The mount is read-only.
Weights are fetched during `truss push` and cached, so cold starts only read from local or nearby caches.

## Custom servers

[Custom Docker servers](/development/model/custom-server) like vLLM and SGLang work directly with BDN. BDN pre-mounts files at `mount_location` before the container starts, so the `start_command` reads weights without a separate download step.

```yaml config.yaml theme={"system"}
base_image:
  image: lmsysorg/sglang:v0.5.8.post1
docker_server:
  start_command: python3 -m sglang.launch_server --model-path /models/qwen
    --served-model-name Qwen/Qwen2.5-3B-Instruct --host 0.0.0.0 --port 8000
  readiness_endpoint: /health
  liveness_endpoint: /health
  predict_endpoint: /v1/chat/completions
  server_port: 8000
weights:
  - source: "hf://Qwen/Qwen2.5-3B-Instruct@aa8e72537993ba99e69dfaafa59ed015b17504d1"
    mount_location: "/models/qwen"
```

For complete worked examples, see [Deploy LLMs with SGLang](/examples/sglang) or [Deploy LLMs with vLLM](/examples/vllm).

## Configuration reference

### `weights`

A list of weight sources to mount into your model container.

```yaml config.yaml theme={"system"}
weights:
  - source: "hf://Qwen/Qwen3-8B@main"
    mount_location: "/models/qwen"
    auth:
      auth_method: CUSTOM_SECRET
      auth_secret_name: "hf_access_token"
    allow_patterns: ["*.safetensors", "*.json", "tokenizer.*"]
    ignore_patterns: ["*.md", "*.txt"]
```

<ParamField type="string">
  URI specifying where to fetch weights from. Supported schemes:

  * `hf://`: Hugging Face Hub.
  * `bt://`: Baseten Training.
  * `s3://`: AWS S3.
  * `gs://`: Google Cloud Storage.
  * `r2://`: Cloudflare R2.

  For Hugging Face sources, specify a revision using `@revision` suffix (branch, tag, or commit SHA).
</ParamField>

<ParamField type="string">
  Absolute path where weights will be mounted in your container. **Must start with `/`**.

  ```yaml theme={"system"}
  mount_location: "/models/qwen"  # Correct
  mount_location: "models/qwen"   # Wrong - not absolute
  ```
</ParamField>

<ParamField type="object">
  Authentication configuration for accessing private weight sources. See [Source types and authentication](#source-types-and-authentication) for the expected format for each source type.

  * `auth_method`: The authentication method. Use `CUSTOM_SECRET` for secret-based auth, `AWS_OIDC` for AWS OIDC, or `GCP_OIDC` for GCP OIDC.
  * `auth_secret_name`: Name of a [Baseten secret](/development/model/secrets) holding the credentials. Required when `auth_method` is `CUSTOM_SECRET`.
</ParamField>

<ParamField type="string[]">
  File patterns to include. Uses Unix shell-style wildcards. Only matching files will be downloaded.

  ```yaml theme={"system"}
  allow_patterns:
    - "*.safetensors"
    - "config.json"
    - "tokenizer.*"
  ```

  Patterns like `*.safetensors` only match files at the top level. Use `**/*.safetensors` to match files in subdirectories.
</ParamField>

<ParamField type="string[]">
  File patterns to exclude. Uses Unix shell-style wildcards. Matching files will be skipped.

  ```yaml theme={"system"}
  ignore_patterns:
    - "*.md"
    - "*.txt"
    - "*.bin"  # Skip PyTorch .bin files if using safetensors
  ```
</ParamField>

## Source types and authentication

For private weight sources, create a [Baseten secret](/development/model/secrets) with the appropriate credentials.
Manage secrets in your [Baseten settings](https://app.baseten.co/settings/secrets).

### Hugging Face

Download weights from Hugging Face Hub repositories.

```yaml config.yaml theme={"system"}
weights:
  - source: "hf://Qwen/Qwen3-8B@main"
    mount_location: "/models/qwen"
    auth:
      auth_method: CUSTOM_SECRET
      auth_secret_name: "hf_access_token"  # Required for private/gated repos
    allow_patterns: ["*.safetensors", "config.json"]
```

**Format:** `hf://owner/repo@revision`

* `owner/repo`: The Hugging Face repository.
* `@revision`: Branch, tag, or commit SHA.

<Note>
  **Revision pinning:** When you use a branch name like `@main`, Baseten resolves it to the specific commit SHA at deploy time and mirrors those exact files. Your deployment stays pinned to that version. Subsequent scale-ups won't pick up new commits. To update to newer weights, push a new deployment.
</Note>

**Authentication:** Hugging Face API token (plain text)

| Secret Name       | Secret Value             |
| ----------------- | ------------------------ |
| `hf_access_token` | `hf_xxxxxxxxxxxxxxxx...` |

Get your token from [Hugging Face settings](https://huggingface.co/settings/tokens).

### Baseten Training

Load weights from a [Baseten Training](/training/overview) checkpoint.

```yaml config.yaml theme={"system"}
weights:
  - source: "bt://my-training-project@job123/checkpoint-1"
    mount_location: "/models/trained"
```

**Format:** `bt://project[@revision][/checkpoint]`

* `project`: The name of your Baseten Training project.
* `@revision`: Optional. A training job ID or `latest`. Defaults to `latest`.
* `/checkpoint`: Optional. The checkpoint name within the training job. If omitted, uses the latest checkpoint.

<Note>
  Baseten automatically authenticates with your training project.
</Note>

### AWS S3

Download weights from a private S3 bucket.

<Tip>
  If your model is small (a few GB or less), you can also [bundle weights directly with your Truss](/development/model/model-class#bundled-data) instead of fetching them from a remote source.
</Tip>

#### Pick an auth method

AWS S3 supports two authentication paths, both first-class:

* **IAM credentials**: Use this if you have an AWS access key pair and want the simplest setup. Skip ahead to the [quick start](#quick-start-with-iam-credentials).
* **AWS OIDC**: Use this if you want short-lived, narrowly scoped tokens and are comfortable configuring an IAM trust policy in your AWS account. See [AWS OIDC](#aws-oidc).

#### Quick start with IAM credentials

Use this path when you already have an AWS access key pair for an IAM user or role with read access to your bucket.

1. **Create the secret in Baseten.** In your [secrets settings](https://app.baseten.co/settings/secrets), add a secret named `aws_credentials` with this JSON value:

   ```json theme={"system"}
   {
     "aws_access_key_id": "AKIA...",
     "aws_secret_access_key": "...",
     "aws_region": "us-west-2"
   }
   ```

   Use these exact key names. Common variations like `access_key_id` (without the `aws_` prefix) cause authentication failures.

2. **Reference the secret from your `config.yaml`:**

   ```yaml config.yaml theme={"system"}
   weights:
     - source: "s3://my-bucket/models/custom-weights"
       mount_location: "/models/custom"
       auth:
         auth_method: CUSTOM_SECRET
         auth_secret_name: "aws_credentials"
   ```

3. **Grant the IAM user the minimum required permissions** on the bucket:

   ```json theme={"system"}
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": ["s3:ListBucket"],
         "Resource": "arn:aws:s3:::my-bucket"
       },
       {
         "Effect": "Allow",
         "Action": ["s3:GetObject"],
         "Resource": "arn:aws:s3:::my-bucket/models/custom-weights/*"
       }
     ]
   }
   ```

   The mirror lists objects under your prefix and downloads each file once. No write permissions are needed.

Push the model. The first deploy mirrors weights to Baseten's blob storage; subsequent deploys reuse the mirror unless the source or filters change.

For the full IAM credentials field reference, including optional fields, see [IAM credentials](#iam-credentials).

#### AWS OIDC

OIDC provides short-lived, narrowly scoped tokens for secure authentication without managing long-lived credentials.

1. [Configure AWS to trust the Baseten OIDC provider](/organization/oidc#aws-setup) and create an IAM role with S3 permissions.

2. Add the OIDC configuration to your `config.yaml`:

```yaml config.yaml theme={"system"}
weights:
  - source: "s3://my-bucket/models/custom-weights"
    mount_location: "/models/custom"
    auth:
      auth_method: AWS_OIDC
      aws_oidc_role_arn: arn:aws:iam::<account-id>:role/baseten-s3-access
      aws_oidc_region: us-west-2
```

<Note>
  No secrets needed. The `aws_oidc_role_arn` and `aws_oidc_region` are not sensitive and can be committed to your repository.
</Note>

See the [OIDC authentication guide](/organization/oidc) for detailed setup instructions and best practices.

#### IAM credentials

```yaml config.yaml theme={"system"}
weights:
  - source: "s3://my-bucket/models/custom-weights"
    mount_location: "/models/custom"
    auth:
      auth_method: CUSTOM_SECRET
      auth_secret_name: "aws_credentials"
```

**Format:** `s3://bucket/path`

**Authentication:** JSON with AWS credentials

| Field                   | Required | Description                                                                            |
| ----------------------- | -------- | -------------------------------------------------------------------------------------- |
| `aws_access_key_id`     | Yes      | Access key ID for the IAM user or role.                                                |
| `aws_secret_access_key` | Yes      | Secret access key paired with the access key ID.                                       |
| `aws_region`            | No       | Region of the bucket. Defaults to `us-east-1`.                                         |
| `aws_session_token`     | No       | Session token for temporary credentials, such as those issued by AWS STS or `aws sso`. |

Example secret value with all fields:

```json theme={"system"}
{
  "aws_access_key_id": "AKIA...",
  "aws_secret_access_key": "...",
  "aws_region": "us-west-2",
  "aws_session_token": "..."
}
```

<Warning>
  The required fields must use the exact names `aws_access_key_id` and `aws_secret_access_key`. Using `access_key_id` or `secret_access_key` (without the `aws_` prefix) causes authentication failures.
</Warning>

For the minimum required IAM policy, see the [quick start](#quick-start-with-iam-credentials).

### Google Cloud Storage

Download weights from a GCS bucket.

GCP supports using either [service accounts](https://cloud.google.com/iam/docs/service-account-overview) or OIDC for GCS authentication.

#### GCP OIDC (recommended)

OIDC provides short-lived, narrowly scoped tokens for secure authentication without managing long-lived credentials.

1. [Configure GCP Workload Identity](/organization/oidc#google-cloud-setup) to trust the Baseten OIDC provider and grant GCS permissions.

2. Add the OIDC configuration to your `config.yaml`:

```yaml config.yaml theme={"system"}
weights:
  - source: "gs://my-bucket/models/weights"
    mount_location: "/models/gcs-weights"
    auth:
      auth_method: GCP_OIDC
      gcp_oidc_service_account: baseten-oidc@my-project.iam.gserviceaccount.com
      gcp_oidc_workload_id_provider: projects/123456789/locations/global/workloadIdentityPools/baseten-pool/providers/baseten-provider
```

<Note>
  No secrets needed. The service account and workload identity provider are not sensitive and can be committed to your repository.
</Note>

See the [OIDC authentication guide](/organization/oidc) for detailed setup instructions and best practices.

#### Service account

```yaml config.yaml theme={"system"}
weights:
  - source: "gs://my-bucket/models/weights"
    mount_location: "/models/gcs-weights"
    auth:
      auth_method: CUSTOM_SECRET
      auth_secret_name: "gcp_service_account"
```

**Format:** `gs://bucket/path`

**Authentication:** GCP service account JSON key

| Secret Name           | Secret Value                                            |
| --------------------- | ------------------------------------------------------- |
| `gcp_service_account` | `{"type": "service_account", "project_id": "...", ...}` |

Download from GCP Console under IAM & Admin > Service Accounts.

### Cloudflare R2

Download weights from a Cloudflare R2 bucket.

```yaml config.yaml theme={"system"}
weights:
  - source: "r2://abc123def.my-bucket/models/weights"
    mount_location: "/models/r2-weights"
    auth:
      auth_method: CUSTOM_SECRET
      auth_secret_name: "r2_credentials"
```

**Format:** `r2://account_id.bucket/path`

* `account_id`: Your Cloudflare account ID.
* `bucket`: R2 bucket name, separated from account\_id by a period.
* `path`: Path prefix within the bucket.

**Authentication:** JSON with R2 API credentials

| Secret Name      | Secret Value                                                   |
| ---------------- | -------------------------------------------------------------- |
| `r2_credentials` | `{"aws_access_key_id": "...", "aws_secret_access_key": "..."}` |

Get your R2 API tokens from the Cloudflare dashboard under R2 > Manage R2 API Tokens.

## Best practices

### Pin to specific commits

<Warning>
  Avoid using branch names like `@main` in production. While Baseten pins to the commit SHA at deploy time, using `@main` means each new deployment may get different weights, making debugging and rollbacks difficult.
</Warning>

Always pin to a specific commit SHA for reproducible deployments:

```yaml config.yaml theme={"system"}
# Recommended - reproducible across deploys
weights:
  - source: "hf://Qwen/Qwen3-8B@<commit-sha>"
    mount_location: "/models/qwen"

# Not recommended for production - each new deployment resolves to a different commit
weights:
  - source: "hf://Qwen/Qwen3-8B@main"
    mount_location: "/models/qwen"
```

To find the current commit SHA for a Hugging Face repo:

```bash Terminal theme={"system"}
# Using the Hugging Face CLI
huggingface-cli repo-info Qwen/Qwen3-8B --revision main
```

### Filter files with patterns

Only download what you need to minimize cold start time:

```yaml config.yaml theme={"system"}
weights:
  - source: "hf://Qwen/Qwen3-8B@main"
    mount_location: "/models/qwen"
    allow_patterns:
      - "*.safetensors"    # Model weights
      - "config.json"      # Model config
      - "tokenizer.*"      # Tokenizer files
    ignore_patterns:
      - "*.bin"            # Skip PyTorch format if using safetensors
      - "*.md"             # Skip documentation
      - "*.txt"            # Skip text files
```

<Warning>
  Patterns like `*.safetensors` only match files at the top level of the source. To match files in subdirectories, use `**/*.safetensors`.
</Warning>

### Use absolute mount paths

The `mount_location` must be an absolute path (starting with `/`):

```yaml config.yaml theme={"system"}
# Correct
mount_location: "/models/qwen"
mount_location: "/app/model_cache/my-model"

# Wrong - will fail validation
mount_location: "models/qwen"
mount_location: "./my-model"
```

### Keep mount locations unique

Each weight source must have a unique `mount_location`:

```yaml config.yaml theme={"system"}
# Correct - different paths
weights:
  - source: "hf://Qwen/Qwen3-8B@main"
    mount_location: "/models/qwen"
  - source: "hf://sentence-transformers/all-MiniLM-L6-v2@main"
    mount_location: "/models/embeddings"

# Wrong - duplicate paths will fail
weights:
  - source: "hf://model-a@main"
    mount_location: "/models/shared"
  - source: "hf://model-b@main"
    mount_location: "/models/shared"
```

### When weights are re-mirrored

Baseten caches weights based on a hash of their configuration and reuses cached weights when possible to avoid redundant downloads.

**Deduplication and mutation detection:**

Baseten deduplicates files based on their etag (a content hash), not just filename, and only re-mirrors files that have been mutated since the last pull. Unchanged files are reused from blob storage, even across deployments.

#### Weight access

A deployment reads only the weight sources it declares in its `weights` config. Caching and deduplication happen behind the scenes and never grant another deployment or organization access to your data. Private sources like S3, GCS, and R2 stay within your organization. Public sources like Hugging Face are already public, so Baseten can serve them from a shared cache across organizations.

**Changes that trigger re-mirroring:**

| Field             | Re-mirrors? | Why                                                                    |
| ----------------- | ----------- | ---------------------------------------------------------------------- |
| `source`          | ✅ Yes       | Different repository, revision, or path                                |
| `allow_patterns`  | ✅ Yes       | Different files will be downloaded                                     |
| `ignore_patterns` | ✅ Yes       | Different files will be downloaded                                     |
| `auth`            | ✅ Yes       | Changing the auth secret name or method changes the configuration hash |

**Changes that do NOT trigger re-mirroring:**

| Field            | Re-mirrors? | Why                                                 |
| ---------------- | ----------- | --------------------------------------------------- |
| `mount_location` | ❌ No        | Only affects where weights appear in your container |

<Tip>
  To force a fresh download of weights that haven't changed, modify the `source` to point to a specific commit SHA instead of a branch name, or add a trivial change to `allow_patterns`.
</Tip>

## How it works

You own the source, and Baseten holds a mirror of it. On `truss push`, BDN reads your `weights` config, mirrors the files into Baseten's secure blob storage, and writes a manifest of content hashes. Files are keyed by hash, so a file BDN already holds is never transferred again, and each deployment mounts only the files in its own manifest.

Your `truss push` returns immediately. Mirroring runs in the background, and your model deploys to the workload plane only after mirroring completes, so weights are in place before your replica starts.

<BdnMirrorDiagram />

### What happens on cold start

Baseten runs workload planes across regions and clusters, each with its own cache tiers. When a replica starts, weights flow from blob storage through the in-cluster cache and the node cache, then are mounted read-only. Each tier serves the one below it, so later replicas read from a warm cache instead of downloading again.

<BdnColdStartFlow />

### Key benefits

* **Non-blocking push** → `truss push` returns immediately; mirroring happens in the background.
* **One-time mirroring** → Weights are mirrored to Baseten storage once, not on every cold start.
* **No upstream dependency at runtime** → Once mirrored, scale-ups and inference never contact the original source.
* **Multi-tier caching** → In-cluster cache prevents redundant downloads; node cache provides instant access for subsequent replicas.
* **Deduplication** → Identical weight files are stored once and shared through hardlinks.
* **Parallel downloads** → Large models download faster with concurrent chunk fetching.

## BDN proxy

<Info>
  BDN proxy is available by request. [Contact us](mailto:support@baseten.co) to enable it for your organization.
</Info>

If your model downloads weights in application code rather than using the `weights` config, BDN proxy can accelerate those downloads. When enabled, Baseten routes your model container's outbound HTTP(S) requests through a distributed caching proxy that caches downloads across cluster nodes. Subsequent replicas and scale-ups serve from cache instead of re-downloading from the origin.

BDN proxy is transparent. You don't need to change your model code. Baseten sets the following environment variables on your container:

| Environment variable | Purpose                                                |
| -------------------- | ------------------------------------------------------ |
| `BDN_PROXY`          | Proxy address.                                         |
| `REQUESTS_CA_BUNDLE` | CA bundle for Python `requests` and other TLS clients. |
| `SSL_CERT_FILE`      | CA bundle for general SSL/TLS clients.                 |
| `PIP_CERT`           | CA bundle for pip.                                     |

<Note>
  BDN proxy does not set `HTTP_PROXY` or `HTTPS_PROXY`. If your model code requires an explicit proxy, use the `BDN_PROXY` environment variable.
</Note>

## Troubleshooting

| Error                                                                        | Cause                                                                                                                                                                                            | Fix                                                                                                                                                                                                                                                                                              |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `aws_access_key_id and aws_secret_access_key are required in S3 credentials` | Secret JSON uses incorrect key names like `access_key_id` instead of `aws_access_key_id`.                                                                                                        | Use the exact key names `aws_access_key_id`, `aws_secret_access_key`, and `aws_region` in your secret JSON.                                                                                                                                                                                      |
| `secret_id is required`                                                      | Your `weights:` source is `s3://` or `r2://` but the config has no `auth:` block, so the mirror can't resolve credentials. Less commonly, the named secret was deleted or hasn't propagated yet. | Add an `auth:` block to the source, like `auth: { auth_method: CUSTOM_SECRET, auth_secret_name: <secret-name> }`. See [AWS S3](#aws-s3) or [Cloudflare R2](#cloudflare-r2) for the per-source format. If the `auth:` block is already present, recreate the secret with a new name and redeploy. |
| `no credentials configured: need either OIDC config or secret_id`            | Your `weights:` source is `gs://` but the config has no `auth:` block.                                                                                                                           | Add an `auth:` block with either `auth_method: GCP_OIDC` and the OIDC fields, or `auth_method: CUSTOM_SECRET` and an `auth_secret_name`. See [Google Cloud Storage](#google-cloud-storage).                                                                                                      |
| Weights download silently skips files in subdirectories                      | `allow_patterns` uses a flat glob like `*.safetensors` that only matches at the top level.                                                                                                       | Use `**/*.safetensors` for recursive matching across subdirectories.                                                                                                                                                                                                                             |
| Weights download completes but model fails to load                           | Required files like `config.json` or tokenizer files are excluded by patterns.                                                                                                                   | Add `config.json` and `tokenizer.*` to `allow_patterns`.                                                                                                                                                                                                                                         |

## Migration from `model_cache`

<Warning>
  `model_cache` is deprecated. Migrate to `weights` for faster cold starts through multi-tier caching.
</Warning>

### Automated migration with `truss migrate`

The `truss migrate` CLI command automatically converts `model_cache` configurations:

```bash Terminal theme={"system"}
# Run in your Truss directory
truss migrate

# Or specify a directory
truss migrate /path/to/truss
```

The command will:

1. Show a colorized diff of the proposed changes.
2. Prompt for confirmation before applying.
3. Create a backup of your original `config.yaml`.
4. Warn about any `model.py` path changes needed.

### Manual migration reference

**From `model_cache` to `weights`:**

| `model_cache`           | `weights`                                 |
| ----------------------- | ----------------------------------------- |
| `repo_id: "owner/repo"` | `source: "hf://owner/repo@rev"`           |
| `revision: "main"`      | Included in source URI as `@main`         |
| `kind: "s3"`            | Prefix: `s3://bucket/path`                |
| `kind: "gcs"`           | Prefix: `gs://bucket/path`                |
| `kind: "r2"`            | Prefix: `r2://account_id.bucket/path`     |
| `volume_folder: "name"` | `mount_location: "/app/model_cache/name"` |
| `runtime_secret_name`   | `auth.auth_secret_name`                   |
| `allow_patterns`        | `allow_patterns` (same)                   |
| `ignore_patterns`       | `ignore_patterns` (same)                  |

**Example migration:**

<Tabs>
  <Tab title="After (weights)">
    ```yaml config.yaml theme={"system"}
    weights:
      - source: "hf://Qwen/Qwen3-8B@main"
        mount_location: "/app/model_cache/qwen"
        allow_patterns:
          - "*.safetensors"
          - "config.json"
        auth:
          auth_method: CUSTOM_SECRET
          auth_secret_name: hf_access_token
    ```
  </Tab>

  <Tab title="Before (model_cache)">
    ```yaml config.yaml theme={"system"}
    model_cache:
      - repo_id: Qwen/Qwen3-8B
        revision: main
        use_volume: true
        volume_folder: qwen
        allow_patterns:
          - "*.safetensors"
          - "config.json"
        runtime_secret_name: hf_access_token
    ```
  </Tab>
</Tabs>

### Chains migration

For Truss Chains, update `Assets.cached` to `Assets.weights` in your Python code:

<Tabs>
  <Tab title="After (weights)">
    ```python theme={"system"}
    import truss_chains as chains
    from truss.base import truss_config

    class MyChainlet(chains.ChainletBase):
        remote_config = chains.RemoteConfig(
            assets=chains.Assets(
                weights=[
                    truss_config.WeightsSource(
                        source="hf://Qwen/Qwen3-8B@main",
                        mount_location="/app/model_cache/qwen",
                        auth_secret_name="hf_access_token",
                        allow_patterns=["*.safetensors", "config.json"],
                    )
                ],
                secret_keys=["hf_access_token"],
            ),
        )
    ```
  </Tab>

  <Tab title="Before (cached)">
    ```python theme={"system"}
    import truss_chains as chains
    from truss.base import truss_config

    class MyChainlet(chains.ChainletBase):
        remote_config = chains.RemoteConfig(
            assets=chains.Assets(
                cached=[
                    truss_config.ModelRepo(
                        repo_id="Qwen/Qwen3-8B",
                        revision="main",
                        use_volume=True,
                        volume_folder="qwen",
                        allow_patterns=["*.safetensors", "config.json"],
                        runtime_secret_name="hf_access_token",
                    )
                ],
                secret_keys=["hf_access_token"],
            ),
        )
    ```
  </Tab>
</Tabs>

**Key changes:**

* `ModelRepo` → `WeightsSource`.
* `repo_id` + `revision` → `source` URI with `@revision` suffix.
* `volume_folder` → `mount_location` (must be absolute path).
* `runtime_secret_name` → `auth.auth_secret_name` (inside an `auth` block with `auth_method: CUSTOM_SECRET`).
* Remove `use_volume` and `kind` (inferred from URI scheme).

### Custom server migration

When migrating an existing custom server deployment from `model_cache` to `weights`:

1. **Remove `truss-transfer-cli`** from your `start_command`. Files are pre-mounted before the container starts.
2. **Update file paths** from `/app/model_cache/{volume_folder}` to your new `mount_location`.

<Tabs>
  <Tab title="After (weights)">
    ```yaml config.yaml theme={"system"}
    docker_server:
      # No truss-transfer-cli needed - weights are pre-mounted
      start_command: text-embeddings-router --port 7997
        --model-id /models/jina --max-client-batch-size 128
    weights:
      - source: "hf://jinaai/jina-embeddings-v2-base-code@516f4baf..."
        mount_location: "/models/jina"
        ignore_patterns: ["*.onnx"]
    ```
  </Tab>

  <Tab title="Before (model_cache)">
    ```yaml config.yaml theme={"system"}
    docker_server:
      # Required truss-transfer-cli to download weights
      start_command: bash -c "truss-transfer-cli && text-embeddings-router --port 7997
        --model-id /app/model_cache/my_jina --max-client-batch-size 128"
    model_cache:
      - repo_id: jinaai/jina-embeddings-v2-base-code
        revision: 516f4baf13dec4ddddda8631e019b5737c8bc250
        use_volume: true
        volume_folder: my_jina
        ignore_patterns: ["*.onnx"]
    ```
  </Tab>
</Tabs>

The [Custom servers](#custom-servers) section shows the pattern for new deployments.

## Automatic use with engine builders

Engine-builder deployments use BDN automatically. No `weights` block is required, and no configuration changes are needed when migrating an existing engine-builder deployment.

| Engine                                                              | When BDN is used |
| ------------------------------------------------------------------- | ---------------- |
| [BEI](/engines/bei/overview)                                        | Every deploy.    |
| [Briton (Engine-Builder-LLM)](/engines/engine-builder-llm/overview) | Every deploy.    |
| [BIS-LLM (V2)](/engines/bis-llm/overview)                           | Every deploy.    |

Build artifacts are mirrored once and served from the same multi-tier caches described in [How it works](#how-it-works).

## Next steps

* [Secrets](/development/model/secrets): Store credentials for private weight sources.
* [Custom Docker images](/development/model/custom-server): Deploy vLLM, SGLang, and other inference servers.
* [Autoscaling](/deployment/autoscaling): Configure replica scaling and cold start behavior.
* [Configuration reference](/reference/truss-configuration#weights): Full list of `weights` options.
