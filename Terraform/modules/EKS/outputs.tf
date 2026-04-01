output "cluster_id" {
  value = aws_eks_cluster.k8s.id
}

output "cluster_name" {
  value = aws_eks_cluster.k8s.name
}

output "cluster_endpoint" {
  value = aws_eks_cluster.k8s.endpoint
}

output "node_group_name" {
  value = aws_eks_node_group.node_grp.node_group_name
}

output "additional_security_group_id" {
  value = aws_security_group.eks_additional_security.id
}

output "node_security_group_id" {
  value = aws_security_group.workernode_sg.id
}