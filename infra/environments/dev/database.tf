resource "aws_db_parameter_group" "app" {
  name_prefix = "cloudops-desk-dev-"
  family      = "postgres17"
  description = "Require encrypted PostgreSQL connections"

  parameter {
    name         = "rds.force_ssl"
    value        = "1"
    apply_method = "pending-reboot"
  }
}

resource "aws_db_instance" "app" {
  identifier     = "cloudops-desk-dev-db"
  engine         = "postgres"
  engine_version = "17.11"
  instance_class = "db.t4g.micro"

  db_name                     = "cloudops"
  username                    = "cloudops_admin"
  manage_master_user_password = true

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_subnet_group_name   = aws_db_subnet_group.app.name
  vpc_security_group_ids = [aws_security_group.database.id]
  parameter_group_name   = aws_db_parameter_group.app.name
  publicly_accessible    = false
  multi_az               = false
  port                   = 5432

  backup_retention_period     = 1
  auto_minor_version_upgrade  = true
  allow_major_version_upgrade = false
  copy_tags_to_snapshot       = true

  deletion_protection       = true
  skip_final_snapshot       = false
  final_snapshot_identifier = "cloudops-desk-dev-db-final"

  tags = {
    Name = "cloudops-desk-dev-db"
  }
}

output "database_address" {
  description = "Private RDS hostname"
  value       = aws_db_instance.app.address
}

output "database_port" {
  value = aws_db_instance.app.port
}

output "database_admin_secret_arn" {
  description = "ARN of the RDS-managed administrator secret"
  value       = aws_db_instance.app.master_user_secret[0].secret_arn
}
