module "vpc" {
  source       = "./modules/VPC"
  cluster_name = var.cluster_name
  cidr         = var.cidr_block
  az           = var.az
  vpc_name     = var.vpc_name
}

module "eks" {
  source       = "./modules/EKS"
  allowed_cidr = var.allowed_cidr
  ami          = var.ami
  eks_name     = var.cluster_name # Reusing cluster_name so they always match
  eks_version  = var.eks_version
  inst_type    = var.inst_type
  max          = var.max
  desired      = var.desired
  min          = var.min
  pubsub       = module.vpc.pubsubid
  pvtsub       = module.vpc.pvtsubid
  vpcid        = module.vpc.vpcid
}