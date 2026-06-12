# deploy/ — multi-cloud staging in under 30 minutes

Terraform deploys the containerized stack (router + every registry backend)
to **GCP Cloud Run** and **AWS App Runner**. Services are cloud-neutral by
architecture rule; everything vendor-specific lives here.

```
deploy/terraform/
  modules/service/   the INTERFACE both vendors implement (see its README)
  gcp/               Cloud Run v2 + Artifact Registry GHCR pull-through
  aws/               App Runner + ECR GHCR pull-through cache
  envs/staging/      composes router+inference on BOTH clouds
```

## Zero → both-cloud staging

**0. Prereqs (5 min).** `terraform >= 1.5`, a GCP project, an AWS account,
and images in GHCR (merge to main once — `containers.yml` publishes them).

**1. Validate locally with no credentials (2 min).**

```bash
cd deploy/terraform/envs/staging
terraform init
terraform validate
terraform plan -var-file=placeholder.tfvars   # placeholder vars, zero creds
```

**2. GCP OIDC (5 min).** Create a Workload Identity Pool + provider for
GitHub (`gcloud iam workload-identity-pools create github ...`), a deployer
service account with `roles/run.admin`, `roles/iam.serviceAccountUser`,
`roles/artifactregistry.admin`, and bind the pool. Save in repo **Variables**:
`GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `GCP_PROJECT`.

**3. AWS OIDC (5 min).** Create an IAM OIDC provider for
`token.actions.githubusercontent.com`, a role trusting your repo with
App Runner/ECR/IAM permissions, and a Secrets Manager secret holding a
GitHub token for the GHCR pull-through. Save: `AWS_DEPLOY_ROLE_ARN`,
`AWS_ACCOUNT_ID`, `AWS_REGION`. **No long-lived keys anywhere.**

**4. Deploy (5 min).** Actions → `deploy-multicloud` → Run workflow →
cloud: `both`, environment: `staging`. The run is gated by
`tools/policy_check.py --action deploy` (agents: staging only; production is
human-only and has no workflow at all). After apply, the workflow writes
each service URL into `routing-policy.yaml`'s endpoint map and commits with
the `[agent:deploy]` trailer — the router immediately has real cross-cloud
candidates for cost-based routing.

**5. Verify (3 min).**

```bash
curl <router-url>/healthz
curl -X POST '<router-url>/v1/predict?model=house-price-reg' \
  -H 'token: <INFERENCE_API_KEY>' -H 'Content-Type: application/json' \
  -d @services/inference/docs/sample_payload.json
```

## State

Local backend by default (`envs/staging/terraform.tfstate`, gitignored —
never commit state). Migration to remote state when the team grows:

```bash
gsutil mb gs://<your-tf-state-bucket>
# in envs/staging/main.tf: backend "gcs" { bucket = "...", prefix = "staging" }
terraform init -migrate-state
```

## Cost guardrails

- Both vendor modules **refuse `max_instances > 3`** (variable validation).
- Cloud Run: `min_instances = 0` for backends → **~$0 idle** (scale-to-zero);
  you pay per-request CPU/memory only.
- App Runner: no scale-to-zero — min 1 instance (~$5/mo idle at 1 vCPU/2 GB
  provisioned). Pause idle staging services with
  `aws apprunner pause-service` to reach ~$0; the registry's
  `scale_to_zero: true` flags which services tolerate that.
- The router prefers the cheaper cloud per `routing-policy.yaml`'s cost
  table, so traffic naturally drains to the lower bidder.

## Agent access (MCP)

`tools/mcp_server.py` exposes `get_cloud_endpoints` and `run_terraform_plan`
(plan is read-only — agents may always run it; apply stays behind the
policy + dispatch-only workflow):

```bash
claude mcp add pipeline -- python3 tools/mcp_server.py
```
