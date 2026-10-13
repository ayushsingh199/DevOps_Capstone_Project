# Credentials are NEVER written here. The AWS provider reads them from the standard chain:
# `aws configure` profile, AWS_PROFILE / AWS_ACCESS_KEY_ID env vars, or SSO.
provider "aws" {
  region = var.region

  default_tags {
    tags = local.tags
  }
}

data "aws_availability_zones" "available" {
  state = "available"
  filter {
    name   = "opt-in-status"
    values = ["opt-in-not-required"]
  }
}

locals {
  name = "${var.project_name}-${var.environment}"
  azs  = slice(data.aws_availability_zones.available.names, 0, var.az_count)

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Repository  = "github.com/ayushsingh199/DevOps_Capstone_Project"
  }
}
