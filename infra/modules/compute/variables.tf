variable "name" {
  description = "Prefix for compute resource names."
  type        = string
}

variable "vpc_id" {
  description = "VPC where the server will run."
  type        = string
}

variable "subnet_id" {
  description = "Public subnet for the server."
  type        = string
}

variable "admin_cidr" {
  description = "Single IPv4 address allowed inbound access."
  type        = string

  validation {
    condition = (
      can(cidrnetmask(var.admin_cidr)) &&
      can(regex("/32$", var.admin_cidr))
    )
    error_message = "Provide a valid IPv4 CIDR ending in /32."
  }
}

variable "ssh_public_key" {
  description = "Public SSH key contents."
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type."
  type        = string
}

variable "ami_id" {
  description = "Pinned AMI for the application server"
  type        = string
}
