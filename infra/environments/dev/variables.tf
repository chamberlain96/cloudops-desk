variable "admin_cidr" {
  description = "Single public IPv4 address allowed to access the server."
  type        = string

  validation {
    condition = (
      can(cidrnetmask(var.admin_cidr)) &&
      can(regex("/32$", var.admin_cidr))
    )
    error_message = "Provide a valid IPv4 CIDR ending in /32."
  }
}

variable "ssh_public_key_path" {
  description = "Local path to the public SSH key."
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for the learning deployment."
  type        = string
  default     = "t3.small"
}
