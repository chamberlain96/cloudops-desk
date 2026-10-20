resource "aws_secretsmanager_secret" "database_app" {
  name                    = "cloudops-desk/dev/database-app"
  description             = "Restricted PostgreSQL credentials for CloudOps Desk"
  recovery_window_in_days = 7
}

resource "aws_iam_role_policy" "database_app_secret_read" {
  name = "read-cloudops-database-app-secret"
  role = module.compute.instance_role_name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = aws_secretsmanager_secret.database_app.arn
    }]
  })
}

output "database_app_secret_arn" {
  description = "Secret holding the restricted application credentials"
  value       = aws_secretsmanager_secret.database_app.arn
}
