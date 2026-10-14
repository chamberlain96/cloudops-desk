variable "name" {
  description = "Prefix used to name network resources."
  type        = string
}

variable "vpc_cidr" {
  description = "IPv4 address range for the VPC."
  type        = string
}

variable "availability_zones" {
  description = "Two distinct Availability Zones."
  type        = list(string)

  validation {
    condition = (
      length(var.availability_zones) == 2 &&
      length(distinct(var.availability_zones)) == 2
    )
    error_message = "Provide exactly two distinct Availability Zones."
  }
}

variable "public_subnet_cidrs" {
  description = "Two public subnet address ranges, in AZ order."
  type        = list(string)

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Provide exactly two public subnet CIDRs."
  }
}

variable "private_subnet_cidrs" {
  description = "Two private subnet address ranges, in AZ order."
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_cidrs) == 2
    error_message = "Provide exactly two private subnet CIDRs."
  }
}
