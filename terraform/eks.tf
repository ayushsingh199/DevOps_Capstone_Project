module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 21.29"

  name               = "${local.name}-eks"
  kubernetes_version = var.kubernetes_version

  # Public endpoint so kubectl/helm work from a laptop; nodes talk to it privately.
  endpoint_public_access       = true
  endpoint_private_access      = true
  endpoint_public_access_cidrs = var.endpoint_public_access_cidrs

  # Whoever runs `terraform apply` becomes cluster admin through an EKS access entry.
  enable_cluster_creator_admin_permissions = true

  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnets
  control_plane_subnet_ids = module.vpc.private_subnets

  addons = {
    vpc-cni = {
      before_compute = true
    }
    eks-pod-identity-agent = {
      before_compute = true
    }
    kube-proxy = {}
    coredns    = {}
    # Persistent volumes for PostgreSQL.
    aws-ebs-csi-driver = {
      pod_identity_association = [{
        role_arn        = aws_iam_role.ebs_csi.arn
        service_account = "ebs-csi-controller-sa"
      }]
    }
    # Resource metrics for `kubectl top` and the Horizontal Pod Autoscaler.
    metrics-server = {}
  }

  eks_managed_node_groups = {
    general = {
      name           = "${local.name}-general"
      ami_type       = "AL2023_x86_64_STANDARD"
      instance_types = var.node_instance_types
      capacity_type  = var.node_capacity_type

      min_size     = var.node_min_size
      max_size     = var.node_max_size
      desired_size = var.node_desired_size

      labels = {
        workload = "general"
      }
    }
  }
}
