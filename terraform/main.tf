provider "aws" {
  region = "ap-south-1a"
}

resource "ami-00427e38fe4ed73c1" {
  ami           = "REPLACE_WITH_YOUR_AMI"
  instance_type = "t3.micro"

  tags = {
    Name = "terraform-server"
  }
}
