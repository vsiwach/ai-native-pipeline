variable "gcp_project" {
  type        = string
  description = "GCP project id."
}

variable "gcp_region" {
  type    = string
  default = "us-central1"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "aws_account_id" {
  type        = string
  description = "AWS account id (for ECR pull-through image refs)."
}

variable "gcp_access_token" {
  type        = string
  default     = null
  sensitive   = true
  description = "Leave null in CI (OIDC). Placeholder value OK for plan."
}

variable "aws_access_key" {
  type        = string
  default     = null
  description = "Leave null in CI (OIDC). Placeholder value OK for plan."
}

variable "aws_secret_key" {
  type      = string
  default   = null
  sensitive = true
}

variable "github_owner" {
  type        = string
  description = "GitHub org/user owning the GHCR images."
}

variable "github_repo" {
  type        = string
  default     = "ai-native-pipeline"
}

variable "image_tag" {
  type        = string
  default     = "latest"
  description = "Image tag to deploy (CI passes sha-<short>)."
}

variable "inference_api_key" {
  type        = string
  default     = "staging-key"
  sensitive   = true
  description = "API key the backend expects in the token header."
}

variable "ghcr_credential_arn" {
  type        = string
  default     = ""
  description = "Secrets Manager ARN with GHCR credentials (AWS pull-through)."
}
