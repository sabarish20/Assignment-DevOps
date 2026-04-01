resource "aws_eks_node_group" "node_grp" {
  cluster_name    = aws_eks_cluster.k8s.name
  node_group_name = "${var.eks_name}-NodeGroup"
  node_role_arn   = aws_iam_role.worker_role.arn
  subnet_ids      = var.pvtsub

  scaling_config {
    desired_size = var.desired
    max_size     = var.max
    min_size     = var.min
  }

  update_config {
    max_unavailable = 1
  }

  instance_types = var.inst_type
  ami_type       = var.ami
  capacity_type  = "ON_DEMAND"
  disk_size      = 20

  tags = {
    Name                                    = "${var.eks_name}-NodeGrp"
    "kubernetes.io/cluster/${var.eks_name}" = "owned"
  }

  depends_on = [
    aws_iam_role_policy_attachment.cni_policy,
    aws_iam_role_policy_attachment.ecr_role_policy,
    aws_iam_role_policy_attachment.worker_role_policy
  ]
}