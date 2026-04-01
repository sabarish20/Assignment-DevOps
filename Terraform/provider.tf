terraform {
  required_version = ">= 1.0"

  backend "s3" {
    bucket = "s3-terraform-jenkins-statefile"
    key    = "cluster/terraform.tfstate"
    region = "ap-south-1"
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.49"
    }
  }
}

provider "aws" {
  region  = "ap-south-1"
}