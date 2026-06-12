# GHCR pull-through: an Artifact Registry REMOTE repository proxying
# ghcr.io, so Cloud Run can pull our GHCR images without mirroring jobs.
# Image refs become:
#   {region}-docker.pkg.dev/{project}/ghcr-remote/{owner}/{repo}/{image}:{tag}

variable "create_ghcr_remote" {
  type        = bool
  default     = false
  description = "Create the shared GHCR remote repo (set true on exactly one module instance per project)."
}

resource "google_artifact_registry_repository" "ghcr_remote" {
  count         = var.create_ghcr_remote ? 1 : 0
  project       = var.project
  location      = var.region
  repository_id = "ghcr-remote"
  format        = "DOCKER"
  mode          = "REMOTE_REPOSITORY"

  remote_repository_config {
    description = "GHCR pull-through cache"
    docker_repository {
      custom_repository {
        uri = "https://ghcr.io"
      }
    }
  }
}
