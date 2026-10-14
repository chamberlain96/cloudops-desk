terraform {
  backend "s3" {
    bucket       = "cloudops-desk-tfstate-eb2bb881"
    key          = "bootstrap/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
