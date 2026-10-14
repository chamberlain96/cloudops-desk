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

module "compute" {
  source = "../../modules/compute"

  name           = "cloudops-desk-dev"
  vpc_id         = module.network.vpc_id
  subnet_id      = module.network.public_subnet_ids[0]
  admin_cidr     = var.admin_cidr
  instance_type  = var.instance_type
  ssh_public_key = file(pathexpand(var.ssh_public_key_path))

  depends_on = [module.network]
}
