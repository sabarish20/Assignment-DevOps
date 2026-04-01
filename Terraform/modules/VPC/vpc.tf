resource "aws_vpc" "action_vpc" {
  cidr_block           = var.cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = {
    Name = var.vpc_name
  }
}

resource "aws_subnet" "pub_sub" {
  vpc_id                                      = aws_vpc.action_vpc.id
  map_public_ip_on_launch                     = true
  count                                       = length(var.az)
  enable_resource_name_dns_a_record_on_launch = true
  cidr_block                                  = cidrsubnet(aws_vpc.action_vpc.cidr_block, 8, count.index + 1)
  availability_zone                           = element(var.az, count.index)
  tags = {
    Name                                        = "Pub-Sub-${count.index}"
    "kubernetes.io/role/elb"                    = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "owned"
  }
}

resource "aws_subnet" "pvt_sub" {
  vpc_id                                      = aws_vpc.action_vpc.id
  count                                       = length(var.az)
  map_public_ip_on_launch                     = false
  enable_resource_name_dns_a_record_on_launch = true
  cidr_block                                  = cidrsubnet(aws_vpc.action_vpc.cidr_block, 8, length(var.az) + count.index + 1)
  availability_zone                           = element(var.az, count.index)
  tags = {
    Name                                        = "Pvt-Sub-${count.index}"
    "kubernetes.io/role/internal-elb"           = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "owned"
  }
}

resource "aws_route_table" "pub_route_table" {
  vpc_id = aws_vpc.action_vpc.id
  tags = {
    Name = "Pub-Route"
  }
}

resource "aws_route" "pub_route" {
  route_table_id         = aws_route_table.pub_route_table.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.igw.id
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.action_vpc.id
  tags = {
    Name = "IGW"
  }
}

resource "aws_route_table_association" "pub_rta" {
  count          = length(var.az)
  subnet_id      = aws_subnet.pub_sub[count.index].id
  route_table_id = aws_route_table.pub_route_table.id
}

resource "aws_eip" "nat_ip" {
  domain = "vpc"
}

resource "aws_nat_gateway" "natgw" {
  subnet_id     = aws_subnet.pub_sub[0].id
  allocation_id = aws_eip.nat_ip.id
  tags = {
    Name = "NatGW"
  }

  depends_on = [aws_internet_gateway.igw]

}

resource "aws_route_table" "pvt_route_table" {
  vpc_id = aws_vpc.action_vpc.id
  tags = {
    Name = "Pvt-Route"
  }
}

resource "aws_route" "pvt_route" {
  route_table_id         = aws_route_table.pvt_route_table.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.natgw.id
}


resource "aws_route_table_association" "pvt_rta" {
  count          = length(var.az)
  subnet_id      = aws_subnet.pvt_sub[count.index].id
  route_table_id = aws_route_table.pvt_route_table.id
}
