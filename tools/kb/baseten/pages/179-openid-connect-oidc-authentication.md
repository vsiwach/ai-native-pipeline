# OpenID Connect (OIDC) authentication
Source: https://docs.baseten.co/organization/oidc

Use short-lived OIDC tokens to securely authenticate to cloud resources

OpenID Connect (OIDC) lets your Baseten deployments authenticate to cloud
resources like S3 buckets and container registries using short-lived tokens
instead of long-lived credentials.

Without OIDC, accessing cloud resources requires long-lived credentials: static
API keys or service account keys stored as secrets in Baseten. These keys don't
expire on their own, so if they're leaked or forgotten, they remain valid until
someone manually rotates them. You're responsible for tracking which keys exist,
where they're used, and when to rotate them.

OIDC takes a different approach. Instead of static keys, Baseten issues
short-lived tokens scoped to a specific deployment. There are no secrets to
store, rotate, or clean up.

Baseten OIDC currently supports:

* **AWS**: Amazon ECR (container images) and Amazon S3 (model weights)
* **Google Cloud**: Artifact Registry, GCR (container images), and Google Cloud Storage (model weights)

## How Baseten OIDC works

Baseten acts as an OIDC identity provider with the following configuration:

* **Issuer**: `https://oidc.baseten.co`
* **Audience**: `oidc.baseten.co`

When you deploy your model, Baseten generates short-lived OIDC tokens that
identify your specific workload. Your cloud provider validates these tokens
against the trust relationship you configure, then grants access to the
specified resources.

## Token structure

Each OIDC token includes standard JWT claims and custom claims that identify the
workload. Here's an example unsigned payload:

```json theme={"system"}
{
  "iss": "https://oidc.baseten.co",
  "sub": "v=1:org=Mvg9jrRd:team=AviIZ0y3:model=kW9wuKFN:deployment=e5f6g7h8:environment=production:type=model_container",
  "aud": "oidc.baseten.co",
  "iat": 1700000000,
  "exp": 1700003600,
  "jti": "550e8400-e29b-41d4-a716-446655440000",
  "org": "Mvg9jrRd",
  "team": "AviIZ0y3",
  "model": "kW9wuKFN",
  "deployment": "e5f6g7h8",
  "environment": "production",
  "type": "model_container"
}
```

The `sub` claim uses a structured format that encodes the workload identity:

```text theme={"system"}
v=1:org={org_id}:team={team_id}:model={model_id}:deployment={deployment_id}:environment={environment}:type={workload_type}
```

### Claim components

| Component     | Description                                                                        | Example       |
| ------------- | ---------------------------------------------------------------------------------- | ------------- |
| `org`         | Your organization ID                                                               | `Mvg9jrRd`    |
| `team`        | Team ID within your organization                                                   | `AviIZ0y3`    |
| `model`       | Model ID                                                                           | `kW9wuKFN`    |
| `deployment`  | Specific deployment/version ID                                                     | `e5f6g7h8`    |
| `environment` | User-defined environment name (max 40 characters). Defaults to `<none>` if not set | `production`  |
| `type`        | Workload type: `model_build` or `model_container`                                  | `model_build` |

### Workload types

* **`model_build`**: Token used during model image building (for example, pulling base images from ECR/GCR).
* **`model_container`**: Token used by running model containers (for example, downloading weights from S3/GCS).

## Subject claim patterns

Common patterns for scoping which workloads can access your resources:

* **AWS**: Use these in the IAM role **trust policy** under `Condition.StringLike` for `oidc.baseten.co:sub`. Wildcards (`*`) are supported.
* **GCP**: Use these in the Workload Identity Provider **attribute-condition**. With the mapping `google.subject=assertion.sub` (see [Create a Workload Identity Provider](#create-a-workload-identity-provider)), reference the sub claim as `google.subject`. GCP does not support wildcards; use `startsWith()` (and `contains()` where needed).

### All workloads in a team

To give every workload in your team access to a resource, match on the team ID with a wildcard for everything else.

<Tabs>
  <Tab title="AWS (trust policy)">
    ```text theme={"system"}
    v=1:org=Mvg9jrRd:team=AviIZ0y3:*
    ```
  </Tab>

  <Tab title="GCP (attribute-condition)">
    ```text theme={"system"}
    google.subject.startsWith('v=1:org=Mvg9jrRd:team=AviIZ0y3:')
    ```
  </Tab>
</Tabs>

### Specific model, all deployments

To restrict access to a single model while allowing all of its deployments and environments, match on the model ID.

<Tabs>
  <Tab title="AWS (trust policy)">
    ```text theme={"system"}
    v=1:org=Mvg9jrRd:team=AviIZ0y3:model=kW9wuKFN:*
    ```
  </Tab>

  <Tab title="GCP (attribute-condition)">
    ```text theme={"system"}
    google.subject.startsWith('v=1:org=Mvg9jrRd:team=AviIZ0y3:model=kW9wuKFN:')
    ```
  </Tab>
</Tabs>

### Specific environment, all models

To scope access by environment, match workloads deployed to a specific environment like `production`.

<Tabs>
  <Tab title="AWS (trust policy)">
    ```text theme={"system"}
    v=1:org=Mvg9jrRd:team=AviIZ0y3:*:environment=production:*
    ```
  </Tab>

  <Tab title="GCP (attribute-condition)">
    ```text theme={"system"}
    google.subject.startsWith('v=1:org=Mvg9jrRd:team=AviIZ0y3:') && google.subject.contains('environment=production')
    ```
  </Tab>
</Tabs>

### Build-time only access

To limit access to the build phase, like pulling base images from a private registry, match on the `model_build` workload type.

<Tabs>
  <Tab title="AWS (trust policy)">
    ```text theme={"system"}
    v=1:org=Mvg9jrRd:team=AviIZ0y3:*:type=model_build
    ```
  </Tab>

  <Tab title="GCP (attribute-condition)">
    ```text theme={"system"}
    google.subject.startsWith('v=1:org=Mvg9jrRd:team=AviIZ0y3:') && google.subject.endsWith('type=model_build')
    ```
  </Tab>
</Tabs>

### Runtime only access

To limit access to running containers, like downloading model weights, match on the `model_container` workload type.

<Tabs>
  <Tab title="AWS (trust policy)">
    ```text theme={"system"}
    v=1:org=Mvg9jrRd:team=AviIZ0y3:*:type=model_container
    ```
  </Tab>

  <Tab title="GCP (attribute-condition)">
    ```text theme={"system"}
    google.subject.startsWith('v=1:org=Mvg9jrRd:team=AviIZ0y3:') && google.subject.endsWith('type=model_container')
    ```
  </Tab>
</Tabs>

### Specific model and environment

To apply the most restrictive access, combine model and environment matching so only a specific model in a specific environment can authenticate.

<Tabs>
  <Tab title="AWS (trust policy)">
    ```text theme={"system"}
    v=1:org=Mvg9jrRd:team=AviIZ0y3:model=kW9wuKFN:*:environment=production:*
    ```
  </Tab>

  <Tab title="GCP (attribute-condition)">
    ```text theme={"system"}
    google.subject.startsWith('v=1:org=Mvg9jrRd:team=AviIZ0y3:model=kW9wuKFN:') && google.subject.contains('environment=production')
    ```
  </Tab>
</Tabs>

## Find your OIDC identifiers

Use [`truss whoami --show-oidc`](/reference/cli/truss/whoami) to view your organization and team IDs, issuer, audience, and subject claim format needed for configuring cloud provider trust policies.

## Cloud provider setup

<Tabs>
  <Tab title="AWS">
    <Accordion title="Provision all resources with a single script">
      Run this script to create the OIDC provider, IAM role, and permission policies. Set the variables at the top, then execute the entire script.

      **Prerequisites**

      * **AWS CLI** [2.x](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
      * **Bash** 3.2+.
      * **AWS credentials** configured for the target account (`aws configure`, environment variables, or an IAM role) with permission to create OIDC identity providers, IAM roles, and inline role policies (for example `iam:CreateOpenIDConnectProvider`, `iam:CreateRole`, `iam:PutRolePolicy`).

      <Warning>
        Review each variable before running. Replace the empty values with your actual AWS account ID, S3 bucket name, organization ID, and team ID.
      </Warning>

      ```bash theme={"system"}
      #!/usr/bin/env bash
      set -euo pipefail

      require_non_empty() {
        local _name="$1"
        local _desc="${2:-$1}"
        local _val
        eval "_val=\${${_name}-}"
        if [ -z "$_val" ]; then
          echo "error: ${_desc} is empty; set ${_name} in the configuration section." >&2
          exit 1
        fi
      }

      # ──────────────────────────────────────────────
      # Configuration: replace these with your values
      # ──────────────────────────────────────────────
      AWS_ACCOUNT_ID=""             # Your AWS account ID
      S3_BUCKET=""                  # S3 bucket for model weights
      ROLE_NAME="BasetenOIDCRole"   # IAM role name
      BASETEN_ORG_ID=""             # From `truss whoami --show-oidc`
      BASETEN_TEAM_ID=""            # From `truss whoami --show-oidc`

      require_non_empty AWS_ACCOUNT_ID "AWS account ID"
      require_non_empty S3_BUCKET "S3 bucket name (model weights)"
      require_non_empty BASETEN_ORG_ID "Baseten organization ID"
      require_non_empty BASETEN_TEAM_ID "Baseten team ID"
      require_non_empty ROLE_NAME "IAM role name"

      OIDC_ISSUER="oidc.baseten.co"
      OIDC_ISSUER_URL="https://${OIDC_ISSUER}"

      # ──────────────────────────────────
      # 1. Create the OIDC identity provider
      # ──────────────────────────────────
      echo "Creating OIDC identity provider..."

      if ! output=$(aws iam create-open-id-connect-provider \
        --url "${OIDC_ISSUER_URL}" 2>&1); then
        if [[ "$output" == *"EntityAlreadyExists"* ]]; then
          echo "OIDC provider already exists, continuing..."
        else
          echo "$output" >&2
          exit 1
        fi
      else
        echo "OIDC provider created."
      fi

      # ──────────────────────────────────
      # 2. Create the IAM trust policy
      # ──────────────────────────────────
      TRUST_POLICY=$(cat <<EOF
      {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Principal": {
              "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/${OIDC_ISSUER}"
            },
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
              "StringEquals": {
                "${OIDC_ISSUER}:aud": "${OIDC_ISSUER}"
              },
              "StringLike": {
                "${OIDC_ISSUER}:sub": "v=1:org=${BASETEN_ORG_ID}:team=${BASETEN_TEAM_ID}:*"
              }
            }
          }
        ]
      }
      EOF
      )

      # ──────────────────────────────────
      # 3. Create the IAM role
      # ──────────────────────────────────
      echo "Creating IAM role ${ROLE_NAME}..."
      aws iam create-role \
        --role-name "${ROLE_NAME}" \
        --assume-role-policy-document "${TRUST_POLICY}" \
        --description "Baseten OIDC role for model workloads"

      echo "IAM role created."

      # ──────────────────────────────────
      # 4. Attach ECR read policy
      # ──────────────────────────────────
      ECR_POLICY=$(cat <<EOF
      {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Action": [
              "ecr:GetAuthorizationToken",
              "ecr:BatchCheckLayerAvailability",
              "ecr:GetDownloadUrlForLayer",
              "ecr:BatchGetImage"
            ],
            "Resource": "*"
          }
        ]
      }
      EOF
      )

      echo "Attaching ECR read policy..."
      aws iam put-role-policy \
        --role-name "${ROLE_NAME}" \
        --policy-name "BasetenECRReadAccess" \
        --policy-document "${ECR_POLICY}"

      # ──────────────────────────────────
      # 5. Attach S3 read policy
      # ──────────────────────────────────
      S3_POLICY=$(cat <<EOF
      {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Action": [
              "s3:GetObject",
              "s3:ListBucket"
            ],
            "Resource": [
              "arn:aws:s3:::${S3_BUCKET}",
              "arn:aws:s3:::${S3_BUCKET}/*"
            ]
          }
        ]
      }
      EOF
      )

      echo "Attaching S3 read policy..."
      aws iam put-role-policy \
        --role-name "${ROLE_NAME}" \
        --policy-name "BasetenS3ReadAccess" \
        --policy-document "${S3_POLICY}"

      # ──────────────────────────────────
      # Done
      # ──────────────────────────────────
      ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${ROLE_NAME}"
      echo ""
      echo "Setup complete. IAM role ARN:"
      echo "  ${ROLE_ARN}"
      echo ""
      echo "Use this role ARN in your Truss configuration."
      ```

      <Note>
        This creates a single role with both ECR and S3 permissions. If you only need ECR **or** S3 access (not both), comment out or remove the policy section you don't need (step 4 or step 5).
      </Note>
    </Accordion>

    If you prefer to walk through each step manually, or need to customize individual resources, follow the instructions below.

    ### Create an OIDC identity provider

    Register Baseten as a trusted OIDC provider in your AWS account.

    1. Navigate to the [AWS IAM Console](https://console.aws.amazon.com/iam/).
    2. Go to **Identity providers** → **Add provider**.
    3. Select **OpenID Connect**.
    4. Configure the provider:
       * **Provider URL**: `https://oidc.baseten.co`
       * Click **Get thumbprint** to verify the provider.
       * **Audience**: `oidc.baseten.co`
    5. Click **Add provider**.

    <Note>
      If your AWS account requires `sts.amazonaws.com` as a trusted audience, add it to the OIDC provider first, then add `oidc.baseten.co` as an additional audience.
    </Note>

    ### Create an IAM role

    Create a role that your Baseten workloads can assume through OIDC.

    1. Go to **Roles** → **Create role**.
    2. Select **Web identity** as the trusted entity type.
    3. Choose the OIDC provider you created.
    4. Select **Audience**: `oidc.baseten.co`, then click **Next**.
    5. On the next page, **attach permissions policies** for the resources your models need to access:

    #### ECR access (for base images)

    Attach this policy to allow pulling container images from ECR.

    ```json theme={"system"}
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": [
            "ecr:GetAuthorizationToken",
            "ecr:BatchCheckLayerAvailability",
            "ecr:GetDownloadUrlForLayer",
            "ecr:BatchGetImage"
          ],
          "Resource": "*"
        }
      ]
    }
    ```

    #### S3 access (for model weights)

    Attach this policy to allow reading model weights from S3.

    ```json theme={"system"}
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": [
            "s3:GetObject",
            "s3:ListBucket"
          ],
          "Resource": [
            "arn:aws:s3:::my-model-weights-bucket",
            "arn:aws:s3:::my-model-weights-bucket/*"
          ]
        }
      ]
    }
    ```

    6. **Configure the trust policy**: Edit the role's trust policy to include subject claim conditions. After creating the role, go to the role → **Trust relationships** → **Edit** and use a policy like this:

    ```json theme={"system"}
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Principal": {
            "Federated": "arn:aws:iam::<aws-account-id>:oidc-provider/oidc.baseten.co"
          },
          "Action": "sts:AssumeRoleWithWebIdentity",
          "Condition": {
            "StringEquals": {
              "oidc.baseten.co:aud": "oidc.baseten.co"
            },
            "StringLike": {
              "oidc.baseten.co:sub": "v=1:org=Mvg9jrRd:team=AviIZ0y3:*"
            }
          }
        }
      ]
    }
    ```

    <Note>
      Replace `<aws-account-id>` with your AWS account ID, and adjust the `sub` claim pattern to match your security requirements.
    </Note>
  </Tab>

  <Tab title="GCP">
    <Accordion title="Provision all resources with a single script">
      Run this script to create the service account, Workload Identity Pool, provider, and role bindings. Set the variables at the top, then execute the entire script.

      **Prerequisites**

      * **Google Cloud SDK** (`gcloud`) [390.0.0+](https://cloud.google.com/sdk/docs/install).
      * **Bash** 3.2+.
      * **gcloud** authenticated (`gcloud auth login` and application-default credentials if needed) with permission to create service accounts, Workload Identity Pools and providers, and modify project IAM (for example **Service Account Admin**, **Workload Identity Pool Admin**, and **Project IAM Admin** or a custom role with equivalent actions on the target project).

      <Warning>
        Review each variable before running. Replace the empty values with your actual GCP project ID, project number, organization ID, and team ID.
      </Warning>

      ```bash theme={"system"}
      #!/usr/bin/env bash
      set -euo pipefail

      require_non_empty() {
        local _name="$1"
        local _desc="${2:-$1}"
        local _val
        eval "_val=\${${_name}-}"
        if [ -z "$_val" ]; then
          echo "error: ${_desc} is empty; set ${_name} in the configuration section." >&2
          exit 1
        fi
      }

      # ──────────────────────────────────────────────
      # Configuration: replace these with your values
      # ──────────────────────────────────────────────
      PROJECT_ID=""                        # Your GCP project ID
      PROJECT_NUMBER=""                    # Your GCP project number
      SERVICE_ACCOUNT_NAME="baseten-oidc"  # Service account name
      POOL_NAME="baseten-pool"             # Workload Identity Pool name
      PROVIDER_NAME="baseten-provider"     # Workload Identity Provider name
      BASETEN_ORG_ID=""                    # From `truss whoami --show-oidc`
      BASETEN_TEAM_ID=""                   # From `truss whoami --show-oidc`

      require_non_empty PROJECT_ID "GCP project ID"
      require_non_empty PROJECT_NUMBER "GCP project number"
      require_non_empty BASETEN_ORG_ID "Baseten organization ID"
      require_non_empty BASETEN_TEAM_ID "Baseten team ID"
      require_non_empty SERVICE_ACCOUNT_NAME "Service account name"
      require_non_empty POOL_NAME "Workload Identity Pool name"
      require_non_empty PROVIDER_NAME "Workload Identity Provider name"

      OIDC_ISSUER_URL="https://oidc.baseten.co"
      OIDC_AUDIENCE="oidc.baseten.co"
      SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

      # ──────────────────────────────────
      # 1. Create the service account
      # ──────────────────────────────────
      echo "Creating service account ${SERVICE_ACCOUNT_NAME}..."
      gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
        --project="${PROJECT_ID}" \
        --display-name="Baseten OIDC Service Account"

      # ──────────────────────────────────
      # 2. Grant Artifact Registry reader
      # ──────────────────────────────────
      echo "Granting Artifact Registry reader role..."
      gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/artifactregistry.reader"

      # ──────────────────────────────────
      # 3. Grant Cloud Storage object viewer
      # ──────────────────────────────────
      echo "Granting Cloud Storage object viewer role..."
      gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="roles/storage.objectViewer"

      # ──────────────────────────────────
      # 4. Create the Workload Identity Pool
      # ──────────────────────────────────
      echo "Creating Workload Identity Pool..."
      gcloud iam workload-identity-pools create "${POOL_NAME}" \
        --project="${PROJECT_ID}" \
        --location="global" \
        --display-name="Baseten Workload Identity Pool"

      # ──────────────────────────────────
      # 5. Create the Workload Identity Provider
      # ──────────────────────────────────
      ATTRIBUTE_CONDITION="google.subject.startsWith('v=1:org=${BASETEN_ORG_ID}:team=${BASETEN_TEAM_ID}:')"

      echo "Creating Workload Identity Provider..."
      gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_NAME}" \
        --project="${PROJECT_ID}" \
        --location="global" \
        --workload-identity-pool="${POOL_NAME}" \
        --issuer-uri="${OIDC_ISSUER_URL}" \
        --allowed-audiences="${OIDC_AUDIENCE}" \
        --attribute-mapping="google.subject=assertion.sub" \
        --attribute-condition="${ATTRIBUTE_CONDITION}"

      # ──────────────────────────────────
      # 6. Allow Workload Identity to impersonate the service account
      # ──────────────────────────────────
      echo "Binding workload identity to service account..."
      gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
        --project="${PROJECT_ID}" \
        --role="roles/iam.workloadIdentityUser" \
        --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_NAME}/*"

      # ──────────────────────────────────
      # Done
      # ──────────────────────────────────
      echo ""
      echo "Setup complete. Service account:"
      echo "  ${SA_EMAIL}"
      echo ""
      echo "Workload Identity Provider:"
      echo "  projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_NAME}/providers/${PROVIDER_NAME}"
      echo ""
      echo "Use these values in your Truss configuration."
      ```

      <Note>
        This grants both Artifact Registry and GCS permissions to the service account. If you only need Artifact Registry **or** GCS access (not both), comment out or remove the role binding you don't need (step 2 or step 3).
      </Note>

      <Note>
        To find your GCP project number, run: `gcloud projects describe PROJECT_ID --format="value(projectNumber)"`
      </Note>
    </Accordion>

    If you prefer to walk through each step manually, or need to customize individual resources, follow the instructions below.

    ### Create a service account

    Create a service account that Baseten workloads will impersonate.

    ```bash theme={"system"}
    gcloud iam service-accounts create baseten-oidc \
      --display-name="Baseten OIDC Service Account"
    ```

    ### Grant permissions to the service account

    Grant the service account access to the resources you need. You can grant one or both depending on your use case.

    #### Artifact Registry access (for base images)

    Grant read access to Artifact Registry for pulling container images.

    ```bash theme={"system"}
    gcloud projects add-iam-policy-binding PROJECT_ID \
      --member="serviceAccount:baseten-oidc@PROJECT_ID.iam.gserviceaccount.com" \
      --role="roles/artifactregistry.reader"
    ```

    #### GCS access (for model weights)

    Grant read access to Cloud Storage for downloading model weights.

    ```bash theme={"system"}
    gcloud projects add-iam-policy-binding PROJECT_ID \
      --member="serviceAccount:baseten-oidc@PROJECT_ID.iam.gserviceaccount.com" \
      --role="roles/storage.objectViewer"
    ```

    ### Create a Workload Identity Pool

    Create a pool to manage external identities from Baseten.

    ```bash theme={"system"}
    gcloud iam workload-identity-pools create baseten-pool \
      --location="global" \
      --display-name="Baseten Workload Identity Pool"
    ```

    ### Create a Workload Identity Provider

    Add Baseten as an OIDC provider in the pool.

    ```bash theme={"system"}
    gcloud iam workload-identity-pools providers create-oidc baseten-provider \
      --location="global" \
      --workload-identity-pool="baseten-pool" \
      --issuer-uri="https://oidc.baseten.co" \
      --allowed-audiences="oidc.baseten.co" \
      --attribute-mapping="google.subject=assertion.sub" \
      --attribute-condition="google.subject.startsWith('v=1:org=Mvg9jrRd:team=AviIZ0y3:')"
    ```

    The **attribute mapping** `google.subject=assertion.sub` maps the OIDC `sub` claim into the `google.subject` attribute. After this mapping, you can use `google.subject` everywhere (including in `attribute-condition`) to reference the subject claim.

    <Warning>
      GCP doesn't support wildcard subject claims. Use `startsWith()` in `attribute-condition` to match workloads by prefix. Replace the organization and team IDs with your own values.
    </Warning>

    ### Allow the Workload Identity to impersonate the service account

    Grant the workload identity pool permission to act as the service account.

    ```bash theme={"system"}
    gcloud iam service-accounts add-iam-policy-binding \
      baseten-oidc@PROJECT_ID.iam.gserviceaccount.com \
      --role="roles/iam.workloadIdentityUser" \
      --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/baseten-pool/*"
    ```
  </Tab>
</Tabs>

## Use OIDC in your Truss configuration

Once you've completed the AWS or GCP setup above, you can configure OIDC authentication in your Truss:

### Private registries (ECR, GCR)

For authenticating to private Docker registries using OIDC, see:

* **[AWS ECR OIDC](/development/model/dependencies#aws-oidc-recommended)**: Configure OIDC for AWS Elastic Container Registry.
* **[GCP Artifact Registry OIDC](/development/model/dependencies#gcp-oidc-recommended)**: Configure OIDC for Google Container Registry / Artifact Registry.

### Model weights (S3, GCS)

For downloading model weights from cloud storage using OIDC, see:

* **[AWS S3 OIDC](/development/model/bdn#aws-oidc)**: Configure OIDC for S3 model weights.
* **[GCS OIDC](/development/model/bdn#gcp-oidc-recommended)**: Configure OIDC for Google Cloud Storage model weights.

## Best practices

### Use least-privilege access

Use the most specific [subject claim pattern](#subject-claim-patterns) that fits your use case. Create separate roles or Workload Identity providers for different environments, workload types, or models rather than one role with broad permissions. Always test your OIDC configuration in a non-production environment first.

<Warning>
  Don't grant access to `v=1:org=*:team=*:*`. This allows any Baseten workload to access your resources.
</Warning>

### Monitor and audit

* Enable CloudTrail (AWS) or Cloud Audit Logs (GCP) to track OIDC token usage.
* Set up alerts for unexpected access patterns.
* Regularly review which roles are being used.

## Troubleshooting

### Authentication failures

If your model fails to authenticate:

1. **Verify the trust relationship**: Ensure your IAM role trusts the Baseten OIDC provider (`https://oidc.baseten.co`).
2. **Check the audience**: Confirm the audience is set to `oidc.baseten.co`.
3. **Review subject claim conditions**: Verify your `sub` claim pattern matches the workload identity.
4. **Inspect your identifiers**: Run `truss whoami --show-oidc` to confirm your org and team IDs.

### Permission denied errors

If authentication succeeds but operations fail:

1. **Check IAM policies**: Ensure the role has the necessary permissions (for example, `s3:GetObject`, `ecr:BatchGetImage`).
2. **Verify resource ARNs**: Confirm bucket names, registry URLs, and other resource identifiers are correct.
3. **Review resource policies**: Some resources (like S3 buckets) have their own policies that may block access.

### Common error messages

| Error                                                     | Likely Cause                            | Solution                                    |
| --------------------------------------------------------- | --------------------------------------- | ------------------------------------------- |
| "Not authorized to perform sts:AssumeRoleWithWebIdentity" | Trust policy doesn't match the workload | Check subject claim pattern in trust policy |
| "Access Denied"                                           | Missing permissions in IAM policy       | Add required permissions to the role        |
| "Invalid identity token"                                  | Issuer or audience mismatch             | Verify OIDC provider configuration          |
| "Token has expired"                                       | Clock skew or token refresh issue       | Contact Baseten support                     |

### Debug with CloudWatch/Cloud Logging

Enable detailed logging to see exactly why authentication or authorization is failing:

**AWS CloudTrail**: Look for `AssumeRoleWithWebIdentity` events to see token validation attempts.

**GCP Cloud Audit Logs**: Check `iam.googleapis.com` logs for workload identity authentication events.

## Migration from long-lived credentials

If you're currently using long-lived AWS or GCP credentials:

1. Set up OIDC as described above.
2. Update your Truss configuration to use OIDC authentication.
3. Deploy and test your model.
4. Once confirmed working, remove the long-lived credentials.
5. Delete any secrets containing long-lived credentials from Baseten.

<Note>
  Both OIDC and long-lived credential authentication methods are supported. You can migrate gradually, starting with non-production environments.
</Note>

## Limitations

* OIDC tokens can't be customized.
* Baseten manages token lifetime and claims.
* Only AWS and GCP services are supported.
* GCP doesn't support wildcard subject claims or subject-based scoping in IAM role conditions. Use the Workload Identity Provider `attribute-condition` instead.
* Cloudflare R2, Azure containers, and Hugging Face aren't yet supported.
