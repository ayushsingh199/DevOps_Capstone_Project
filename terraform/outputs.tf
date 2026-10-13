output "region" {
  description = "AWS region."
  value       = var.region
}

output "vpc_id" {
  description = "ID of the VPC."
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs (load balancers, NAT gateway)."
  value       = module.vpc.public_subnets
}

output "private_subnet_ids" {
  description = "Private subnet IDs (worker nodes)."
  value       = module.vpc.private_subnets
}

output "cluster_name" {
  description = "EKS cluster name."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS API server endpoint."
  value       = module.eks.cluster_endpoint
}

output "cluster_version" {
  description = "Kubernetes version of the control plane."
  value       = module.eks.cluster_version
}

output "node_group_names" {
  description = "Managed node group names."
  value       = [for ng in module.eks.eks_managed_node_groups : ng.node_group_id]
}

output "configure_kubectl" {
  description = "Command that writes a kubeconfig entry for this cluster."
  value       = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}
