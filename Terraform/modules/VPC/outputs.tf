output "pubsubid" {
  value = aws_subnet.pub_sub[*].id
}

output "pvtsubid" {
  value = aws_subnet.pvt_sub[*].id
}

output "vpcid" {
  value = aws_vpc.action_vpc.id
}
