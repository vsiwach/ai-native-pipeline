# The service module INTERFACE — the portability claim of this repo.
# Both vendor modules (../../gcp, ../../aws) implement exactly these
# variables and the `url` output. Composing a service onto a cloud means
# swapping the module source, nothing else.

variable "service_name" {
  type        = string
  description = "Name of the deployed service (registry key)."
}

variable "image" {
  type        = string
  description = "Full container image reference the cloud can pull."
}

variable "cpu" {
  type        = string
  default     = "1"
  description = "vCPUs per instance (vendor modules translate units)."
}

variable "memory" {
  type        = string
  default     = "512Mi"
  description = "Memory per instance (vendor modules translate units)."
}

variable "min_instances" {
  type        = number
  default     = 0
  description = "Min replicas. 0 = scale-to-zero where the vendor supports it."
}

variable "max_instances" {
  type        = number
  default     = 3
  description = "Max replicas. Cost guardrail: keep <= 3 in staging."

  validation {
    condition     = var.max_instances <= 3
    error_message = "Cost guardrail: max_instances must be <= 3 (see deploy/README.md)."
  }
}

variable "port" {
  type        = number
  default     = 8080
  description = "Container port serving the inference contract."
}

variable "env" {
  type        = map(string)
  default     = {}
  description = "Environment variables for the container."
}
