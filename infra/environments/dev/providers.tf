provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = "CloudOps Desk"
      Environment = "dev"
      ManagedBy   = "Terraform"
    }
  }
}
