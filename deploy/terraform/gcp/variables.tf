# Implements the modules/service interface — keep in lockstep with
# deploy/terraform/modules/service/variables.tf.

variable "service_name" {
  type = string
}

variable "image" {
  type = string
}

variable "cpu" {
  type    = string
  default = "1"
}

variable "memory" {
  type    = string
  default = "512Mi"
}

variable "min_instances" {
  type    = number
  default = 0
}

variable "max_instances" {
  type    = number
  default = 3

  validation {
    condition     = var.max_instances <= 3
    error_message = "Cost guardrail: max_instances must be <= 3 (see deploy/README.md)."
  }
}

variable "port" {
  type    = number
  default = 8080
}

variable "env" {
  type    = map(string)
  default = {}
}
