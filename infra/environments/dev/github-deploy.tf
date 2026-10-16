resource "aws_iam_role" "github_deploy" {
  name = "cloudops-desk-github-deploy"

  assume_role_policy = aws_iam_role.github_ecr_publish.assume_role_policy
}

resource "aws_iam_role_policy" "github_deploy" {
  name = "invoke-cloudops-release"
  role = aws_iam_role.github_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "RunDedicatedRelease"
        Effect = "Allow"
        Action = ["ssm:SendCommand"]
        Resource = [
          aws_ssm_document.release.arn,
          "arn:aws:ec2:us-east-1:595540521786:instance/${module.compute.instance_id}"
        ]
      },
      {
        Sid      = "ReadCommandResult"
        Effect   = "Allow"
        Action   = ["ssm:GetCommandInvocation"]
        Resource = "*"
      },
      {
        Sid      = "VerifyImageInRepository"
        Effect   = "Allow"
        Action   = ["ecr:DescribeImages"]
        Resource = aws_ecr_repository.cloudops_desk.arn
      }
    ]
  })
}

output "github_deploy_role_arn" {
  description = "GitHub role for invoking the application release"
  value       = aws_iam_role.github_deploy.arn
}
