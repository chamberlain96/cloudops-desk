resource "aws_ecr_repository" "cloudops_desk" {
  name                 = "cloudops-desk"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = true
  }
}

output "ecr_repository_url" {
  description = "Registry address for CloudOps Desk images"
  value       = aws_ecr_repository.cloudops_desk.repository_url
}

output "ecr_repository_arn" {
  description = "Repository ARN for scoped IAM permissions"
  value       = aws_ecr_repository.cloudops_desk.arn
}
