data "aws_availability_zones" "available" {
  state = "available"

  filter {
    name   = "zone-type"
    values = ["availability-zone"]
  }
}

module "network" {
  source = "../../modules/network"

  name     = "cloudops-desk-dev"
  vpc_cidr = "10.20.0.0/16"
  availability_zones = slice(
    sort(data.aws_availability_zones.available.names), 0, 2
  )

  public_subnet_cidrs = [
    "10.20.1.0/24",
    "10.20.2.0/24",
  ]

  private_subnet_cidrs = [
    "10.20.11.0/24",
    "10.20.12.0/24",
  ]
}
