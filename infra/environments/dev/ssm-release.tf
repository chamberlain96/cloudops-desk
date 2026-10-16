resource "aws_ssm_document" "release" {
  name            = "CloudOpsDesk-Release"
  document_type   = "Command"
  document_format = "JSON"

  content = jsonencode({
    schemaVersion = "2.2"
    description   = "Deploy CloudOps Desk using local Ansible with rollback"

    parameters = {
      ImageUri = {
        type              = "String"
        description       = "CloudOps Desk ECR image pinned by digest"
        interpolationType = "ENV_VAR"
        allowedPattern    = "^595540521786[.]dkr[.]ecr[.]us-east-1[.]amazonaws[.]com/cloudops-desk@sha256:[a-f0-9]{64}$"
      }
    }

    mainSteps = [{
      action = "aws:runShellScript"
      name   = "DeployApplication"

      precondition = {
        StringEquals = ["platformType", "Linux"]
      }

      inputs = {
        timeoutSeconds = "900"
        runCommand = [
          "set -eu",
          "export ANSIBLE_COLLECTIONS_PATH=/opt/cloudops-ansible/collections",
          "/usr/bin/flock -n /var/lock/cloudops-release.lock /opt/cloudops-ansible/bin/ansible-playbook -i /opt/cloudops-desk/automation/inventory/local.ini /opt/cloudops-desk/automation/release.yml -e \"cloudops_image=$SSM_ImageUri\""
        ]
      }
    }]
  })
}

output "ssm_release_document_name" {
  value = aws_ssm_document.release.name
}
