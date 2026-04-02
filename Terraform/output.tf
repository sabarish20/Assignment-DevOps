output "cluster_id" {
  value = module.eks.cluster_id
}

output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "node_group_name" {
  value = module.eks.node_group_name
}

output "additional_security_group_id" {
  value = module.eks.additional_security_group_id
}

output "pubsubid" {
  value = module.vpc.pubsubid
}

output "pvtsubid" {
  value = module.vpc.pvtsubid
}

output "vpcid" {
  value = module.vpc.vpcid
}

output "node_security_group_id" {
  value = module.eks.node_security_group_id
}

output "aws_load_balancer_controller_role_arn" {
  value = aws_iam_role.aws_load_balancer_controller.arn
}