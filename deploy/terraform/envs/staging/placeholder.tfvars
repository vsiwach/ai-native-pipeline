# Documented placeholder vars — enough for `terraform validate` and
# `terraform plan` with ZERO real credentials (acceptance criterion).
# Real values come from GitHub OIDC + repo variables in CI.
gcp_project      = "my-staging-project"
gcp_access_token = "placeholder-plan-only"
aws_account_id = "123456789012"
aws_access_key = "PLACEHOLDER"
aws_secret_key = "PLACEHOLDER"
github_owner   = "my-github-user"
