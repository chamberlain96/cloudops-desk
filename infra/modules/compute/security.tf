terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

resource "aws_security_group" "app" {
  name_prefix = "${var.name}-"
  description = "Restricted access to CloudOps Desk"
  vpc_id      = var.vpc_id

  tags = {
    Name = "${var.name}-sg"
  }
}

resource "aws_vpc_security_group_ingress_rule" "ssh" {
  security_group_id = aws_security_group.app.id
  description       = "SSH from administrator IP"
  cidr_ipv4         = var.admin_cidr
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
}

resource "aws_vpc_security_group_ingress_rule" "application" {
  security_group_id = aws_security_group.app.id
  description       = "Application access from administrator IP"
  cidr_ipv4         = var.admin_cidr
  ip_protocol       = "tcp"
  from_port         = 5000
  to_port           = 5000
}

resource "aws_vpc_security_group_egress_rule" "outbound" {
  security_group_id = aws_security_group.app.id
  description       = "Outbound access for updates and image downloads"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}
