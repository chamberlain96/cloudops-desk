resource "aws_db_subnet_group" "app" {
  name       = "cloudops-desk-dev-db"
  subnet_ids = module.network.private_subnet_ids

  tags = {
    Name = "cloudops-desk-dev-db"
  }
}

resource "aws_security_group" "database" {
  name_prefix = "cloudops-desk-dev-db-"
  description = "PostgreSQL access from the application security group"
  vpc_id      = module.network.vpc_id

  tags = {
    Name = "cloudops-desk-dev-db"
  }
}

resource "aws_vpc_security_group_ingress_rule" "database_from_app" {
  security_group_id            = aws_security_group.database.id
  referenced_security_group_id = module.compute.security_group_id

  ip_protocol = "tcp"
  from_port   = 5432
  to_port     = 5432
  description = "PostgreSQL from application instances"
}
