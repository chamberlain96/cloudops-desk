output "instance_id" {
  value = aws_instance.app.id
}

output "public_ip" {
  value = aws_instance.app.public_ip
}

output "security_group_id" {
  value = aws_security_group.app.id
}

output "instance_role_name" {
  description = "IAM role used by the application server"
  value       = aws_iam_role.app.name
}
