# PHASE 4 — Multi-cloud deployment (Terraform)

Paste everything below into Claude Code.

---

Deploy the containerized stack to two clouds with Terraform: GCP Cloud Run and
AWS App Runner. Cloud-neutral services, vendor-specific IaC only.

## Tasks
1. Layout:
   ```
   deploy/terraform/
     modules/service/        # interface: image, cpu, memory, min/max instances, env
     gcp/                    # Cloud Run v2 implementation + artifact registry pull
     aws/                    # App Runner implementation + ECR or GHCR pull-through
     envs/staging/main.tf    # composes: router+inference on BOTH clouds
   ```
   The `modules/service` interface is the portability claim — both vendor modules
   implement the same variables. `scale_to_zero: true` in the registry maps to
   min instances 0 (Cloud Run) / auto-pause (App Runner).
2. State: local backend with documented migration path to remote state; never
   commit state files (extend .gitignore).
3. New workflow `.github/workflows/deploy-multicloud.yml`:
   - `workflow_dispatch` with inputs: cloud (gcp|aws|both), environment (staging)
   - Auth via OIDC (google-github-actions/auth, aws-actions/configure-aws-credentials)
     — document required GitHub repo settings in deploy/README.md; NO long-lived keys
   - terraform plan on PRs touching deploy/** (plan posted as PR comment);
     apply only via dispatch, gated by `policy_check.py --action deploy`
4. After apply, write each service URL into `routing-policy.yaml`'s endpoint map
   (terraform output → small python script → commit `[agent:deploy]` trailer).
   The router now has real cross-cloud candidates for cost-based routing.
5. Extend the MCP server with `get_cloud_endpoints` and `run_terraform_plan` tools
   (plan is read-only — agents may always run it; apply stays behind the policy).
6. Cost guardrails: both modules set max instances ≤ 3 and document the ~$0 idle
   cost (scale-to-zero) in deploy/README.md.

## Acceptance criteria
- `terraform validate` and `terraform plan` succeed in envs/staging with documented
  placeholder vars (no real creds needed to validate)
- CI posts a plan comment on a PR touching deploy/**
- policy_check refuses `--action deploy --env production --requested-by claude`
- deploy/README.md walks a new dev from zero to both-cloud staging in <30 min
