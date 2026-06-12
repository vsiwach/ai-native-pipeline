# AWS implementation of modules/service: App Runner.
# App Runner has no true scale-to-zero: min size is 1. The registry's
# scale_to_zero maps to "pausable" — `aws apprunner pause-service` drops
# idle cost to ~$0; deploy/README.md documents the trade-off.

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

resource "aws_apprunner_auto_scaling_configuration_version" "service" {
  auto_scaling_configuration_name = substr("${var.service_name}-asc", 0, 32)
  min_size                        = max(var.min_instances, 1) # App Runner floor
  max_size                        = var.max_instances
}

resource "aws_apprunner_service" "service" {
  service_name = var.service_name

  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.service.arn

  source_configuration {
    auto_deployments_enabled = false

    image_repository {
      image_repository_type = "ECR" # via the GHCR pull-through cache (ecr.tf)
      image_identifier      = var.image

      image_configuration {
        port                          = tostring(var.port)
        runtime_environment_variables = var.env
      }
    }

    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }
  }

  instance_configuration {
    cpu    = var.cpu    # e.g. "1024" (1 vCPU)
    memory = var.memory # e.g. "2048" (2 GB)
  }

  health_check_configuration {
    protocol = "HTTP"
    path     = "/healthz"
  }
}

resource "aws_iam_role" "apprunner_ecr_access" {
  name = substr("${var.service_name}-apprunner-ecr", 0, 64)

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "build.apprunner.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_access" {
  role       = aws_iam_role.apprunner_ecr_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

output "url" {
  value       = "https://${aws_apprunner_service.service.service_url}"
  description = "Public HTTPS URL of the deployed service."
}
