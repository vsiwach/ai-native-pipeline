# Implements the modules/service interface — keep in lockstep with
# deploy/terraform/modules/service/variables.tf.
# Note: App Runner cpu/memory take numeric strings ("1024", "2048") —
# envs/staging translates from the neutral units.

variable "service_name" {
  type = string
}

variable "image" {
  type = string
}

variable "cpu" {
  type    = string
  default = "1024"
}

variable "memory" {
  type    = string
  default = "2048"
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
