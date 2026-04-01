resource "aws_security_group" "eks_additional_security" {
  name_prefix = "${var.eks_name}-Additional-SG"
  vpc_id      = var.vpcid

  tags = {
    Name                                    = "${var.eks_name}-Additional-SG"
    "kubernetes.io/cluster/${var.eks_name}" = "owned"
  }
}

resource "aws_security_group_rule" "ingress_https" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.eks_additional_security.id
  source_security_group_id = aws_security_group.eks_additional_security.id
}

resource "aws_security_group" "workernode_sg" {
  name_prefix = "${var.eks_name}-Node-SG"
  vpc_id      = var.vpcid

  tags = {
    Name                                    = "${var.eks_name}-WorkerNode-SG"
    "kubernetes.io/cluster/${var.eks_name}" = "owned"
  }
}

resource "aws_security_group_rule" "workernode_egress_sg" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = aws_security_group.workernode_sg.id
  cidr_blocks       = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "workernode_between_sg" {
  type                     = "ingress"
  from_port                = "0"
  to_port                  = "0"
  protocol                 = "-1"
  security_group_id        = aws_security_group.workernode_sg.id
  source_security_group_id = aws_security_group.workernode_sg.id
}

resource "aws_security_group_rule" "control_to_node" {
  type                     = "ingress"
  from_port                = "0"
  to_port                  = "0"
  protocol                 = "-1"
  security_group_id        = aws_security_group.workernode_sg.id
  source_security_group_id = aws_security_group.eks_additional_security.id
}

resource "aws_security_group_rule" "api_to_node" {
  type                     = "ingress"
  from_port                = "443"
  to_port                  = "443"
  protocol                 = "tcp"
  security_group_id        = aws_security_group.eks_additional_security.id
  source_security_group_id = aws_security_group.workernode_sg.id
}