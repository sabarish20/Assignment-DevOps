resource "aws_eks_cluster" "k8s" {
  name     = var.eks_name
  role_arn = aws_iam_role.k8s_role.arn
  version  = var.eks_version

  access_config {
    authentication_mode                         = "API_AND_CONFIG_MAP"
    bootstrap_cluster_creator_admin_permissions = true
  }

  vpc_config {
    endpoint_private_access = false
    endpoint_public_access  = true
    public_access_cidrs     = var.allowed_cidr
    security_group_ids      = [aws_security_group.eks_additional_security.id]
    subnet_ids              = concat(var.pubsub, var.pvtsub)
  }

  enabled_cluster_log_types = ["api", "audit"]

  depends_on = [
    aws_iam_role_policy_attachment.k8s_role_policy

  ]

  tags = {
    Name = var.eks_name
  }
}