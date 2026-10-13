# Network layout (per AZ):
#   public subnet  -> internet gateway; hosts the NAT gateway and internet-facing load balancers
#   private subnet -> NAT gateway;      hosts the EKS worker nodes (no public IPs)
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 6.7"

  name = "${local.name}-vpc"
  cidr = var.vpc_cidr
  azs  = local.azs

  public_subnets  = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, i)]
  private_subnets = [for i, _ in local.azs : cidrsubnet(var.vpc_cidr, 8, i + 10)]

  enable_nat_gateway   = true
  single_nat_gateway   = var.single_nat_gateway
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Tags that let Kubernetes place internet-facing / internal load balancers in the right subnets.
  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}
