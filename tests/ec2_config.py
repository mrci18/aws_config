import boto3
from sg_config import CustomSG

class CustomEC2:
    def __init__(self):
        self.ec2_resource = boto3.resource('ec2')

    def create_ec2(self, sg_id):
        self.ec2_resource.create_instances(MaxCount=1, MinCount=1, ImageId='ami-087c2c50437d0b80d', SecurityGroupIds=[sg_id])

    def main(self):
        public_sg_ids = CustomSG().main()
        self.create_ec2(public_sg_ids[0])
        self.create_ec2(public_sg_ids[1])
