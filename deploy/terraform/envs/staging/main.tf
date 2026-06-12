# Staging: router + inference backend on BOTH clouds.
# The services map mirrors inference-registry.yaml; the two for_each blocks
# are the portability proof — same inputs, different vendor module.

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Local state for now. Migration path to remote state (documented in
  # deploy/README.md): create a GCS bucket, then `terraform init -migrate-state`
  # with: backend "gcs" { bucket = "<bucket>", prefix = "staging" }
  backend "local" {}
}

provider "google" {
  project = var.gcp_project
  region  = var.gcp_region

  # Placeholder token lets plan/validate run with zero real credentials
  # (create-only plans make no API calls). Leave null in CI — OIDC supplies
  # application-default credentials there.
  access_token = var.gcp_access_token
}

provider "aws" {
  region = var.aws_region

  # Allow plan/validate with the documented placeholder vars — no real
  # credentials are needed until apply (CI applies via OIDC).
  skip_credentials_validation = true
  skip_requesting_account_id  = true
  skip_metadata_api_check     = true
  access_key                  = var.aws_access_key
  secret_key                  = var.aws_secret_key
}

locals {
  # Mirrors inference-registry.yaml (tier/target stay in the registry; this
  # is purely the per-cloud runtime shape).
  services = {
    router = {
      port          = 8080
      min_instances = 1 # the public entry stays warm
      max_instances = 3
      env           = {}
    }
    inference = {
      port          = 8080
      min_instances = 0 # scale_to_zero: true in the registry
      max_instances = 3
      env           = { INFERENCE_API_KEY = var.inference_api_key }
    }
  }

  gcp_image = {
    for name, _ in local.services :
    name => "${var.gcp_region}-docker.pkg.dev/${var.gcp_project}/ghcr-remote/${var.github_owner}/${var.github_repo}/${name}:${var.image_tag}"
  }
  aws_image = {
    for name, _ in local.services :
    name => "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/ghcr/${var.github_owner}/${var.github_repo}/${name}:${var.image_tag}"
  }
}

module "gcp" {
  source   = "../../gcp"
  for_each = local.services

  project       = var.gcp_project
  region        = var.gcp_region
  service_name  = "${each.key}-staging"
  image         = local.gcp_image[each.key]
  port          = each.value.port
  min_instances = each.value.min_instances
  max_instances = each.value.max_instances
  env           = each.value.env

  # one shared GHCR remote repo per project
  create_ghcr_remote = each.key == "router"
}

module "aws" {
  source   = "../../aws"
  for_each = local.services

  service_name  = "${each.key}-staging"
  image         = local.aws_image[each.key]
  port          = each.value.port
  min_instances = each.value.min_instances
  max_instances = each.value.max_instances
  env           = each.value.env
  cpu           = "1024" # 1 vCPU — App Runner numeric units
  memory        = "2048" # 2 GB

  # one shared pull-through rule per account
  create_ghcr_pull_through = each.key == "router"
  ghcr_credential_arn      = each.key == "router" ? var.ghcr_credential_arn : ""
}

output "gcp_urls" {
  value       = { for name, m in module.gcp : name => m.url }
  description = "Cloud Run URLs per service."
}

output "aws_urls" {
  value       = { for name, m in module.aws : name => m.url }
  description = "App Runner URLs per service."
}
