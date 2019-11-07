import sys
sys.path.append("../")
sys.path.append("../../check_sg_port_ingress/")

import unittest
import boto3
from moto import mock_ec2
from sg_config import CustomSG
from check_sg_port_ingress import Ec2Actions, lambda_handler

@mock_ec2
def setUpModule():
    public_sgs = CustomSG().main()
    client = boto3.client('ec2')
    response = client.describe_security_groups()
    all_sgs = response['SecurityGroups']
    Ec2Actions().evaluate_each_sg(public_sgs, all_sgs)
    
@mock_ec2
class TestSGPortIngress(unittest.TestCase):
    def test_check_lowercase_public_sg_cidr(self):
        client = boto3.client('ec2')
        response = client.describe_security_groups(GroupNames=['SG2', 'SG7'])
        security_groups = response['SecurityGroups']
        for security_group in security_groups:
            cidr_ip = security_group['IpPermissions'][0]['IpRanges'][0]['CidrIp']
            self.assertEqual(cidr_ip, '0.0.0.0/0')

    def test_check_open_private_sg_cidr(self):
        client = boto3.client('ec2')
        response = client.describe_security_groups(GroupNames=['SG3', 'SG4', 'SG8', 'SG10'])
        security_groups = response['SecurityGroups']
        for security_group in security_groups:
            cidr_ip = security_group['IpPermissions'][1]['IpRanges'][0]['CidrIp']
            self.assertEqual(cidr_ip, '10.0.0.0/8')

    def test_open_public_sg_cidr(self):
        client = boto3.client('ec2')
        response = client.describe_security_groups(GroupNames=['SG1', 'SG2', 'SG6', 'SG7'])
        security_groups = response['SecurityGroups']
        for security_group in security_groups:
            ip_permissions = security_group['IpPermissions']
            self.assertEqual(len(ip_permissions), 1)
            
            cidr_ip = security_group['IpPermissions'][0]['IpRanges'][0]['CidrIp']
            self.assertEqual(cidr_ip, '0.0.0.0/0')
