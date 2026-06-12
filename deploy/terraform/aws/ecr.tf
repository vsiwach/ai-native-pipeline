# GHCR pull-through: ECR pull-through cache rule proxying ghcr.io, so App
# Runner (ECR-only) can pull our GHCR images without mirroring jobs.
# Image refs become:
#   {account}.dkr.ecr.{region}.amazonaws.com/ghcr/{owner}/{repo}/{image}:{tag}

variable "create_ghcr_pull_through" {
  type        = bool
  default     = false
  description = "Create the shared GHCR pull-through rule (set true on exactly one module instance per account)."
}

variable "ghcr_credential_arn" {
  type        = string
  default     = ""
  description = "Secrets Manager ARN holding a GitHub username/token for ghcr.io (required when create_ghcr_pull_through)."
}

resource "aws_ecr_pull_through_cache_rule" "ghcr" {
  count                 = var.create_ghcr_pull_through ? 1 : 0
  ecr_repository_prefix = "ghcr"
  upstream_registry_url = "ghcr.io"
  credential_arn        = var.ghcr_credential_arn
}
