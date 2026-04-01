terraform {
  backend "s3" {
    bucket = "s3-terraform-jenkins-statefile"
    key    = "s3-provisioning/terraform.tfstate"
    region = "ap-south-1"
  }
}

provider "aws" {
  region = "ap-south-1"
}
resource "aws_s3_bucket" "s3_bucket" {
  bucket = "jenkins-sample-s3bucket-as1-terraform"
}
