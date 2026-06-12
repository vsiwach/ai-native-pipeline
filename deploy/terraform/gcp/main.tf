# GCP implementation of modules/service: Cloud Run v2.
# scale_to_zero: true in the registry maps to min_instance_count = 0 —
# idle cost ~$0 (see deploy/README.md cost guardrails).

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

variable "project" {
  type        = string
  description = "GCP project id."
}

variable "region" {
  type        = string
  default     = "us-central1"
}

resource "google_cloud_run_v2_service" "service" {
  name     = var.service_name
  location = var.region
  project  = var.project
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = var.min_instances
      max_instance_count = var.max_instances
    }

    containers {
      image = var.image

      ports {
        container_port = var.port
      }

      resources {
        limits = {
          cpu    = var.cpu
          memory = var.memory
        }
      }

      dynamic "env" {
        for_each = var.env
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }
}

# Backends sit behind the router; the router itself is the public entry.
# Staging keeps everything invoker-public for simplicity — lock down with
# IAM once the router gets a service identity.
resource "google_cloud_run_v2_service_iam_member" "public" {
  name     = google_cloud_run_v2_service.service.name
  location = var.region
  project  = var.project
  role     = "roles/run.invoker"
  member   = "allUsers"
}

output "url" {
  value       = google_cloud_run_v2_service.service.uri
  description = "Public HTTPS URL of the deployed service."
}
