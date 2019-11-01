import boto3
# from moto import mock_ec2

class CustomEc2:
    def __init__(self):
        self.client = boto3.client('ec2')

    def create_sg(self, group_name, from_port, to_port, ip_protocol, cidr_ip, tag, cidr_ipv6=False):
        sg_creation_response = self.client.create_security_group(
            Description='string',
            GroupName=group_name
        )
        group_id = sg_creation_response['GroupId']

        authorize_sg_ingress_response = self.client.authorize_security_group_ingress(
            GroupId=group_id,
            IpPermissions=[
                {
                    'FromPort': from_port,
                    'IpProtocol': ip_protocol,
                    'IpRanges': [
                        {
                            'CidrIp': cidr_ip,
                            'Description': 'Creted by moto'
                        },
                    ],
                    'ToPort': to_port
                }
            ]

        ) 

        create_tag_response = self.client.create_tags(
            Resources=[group_id
            ],
            Tags=[
                {
                    'Key': 'Confidentiality',
                    'Value': tag
                },
            ]
        )
        if cidr_ipv6:
            authorize_sg_ipv6_ingress_response = self.client.authorize_security_group_ingress(
                GroupId=group_id,
                IpPermissions=[
                    {
                        'FromPort': from_port,
                        'IpProtocol': ip_protocol,
                        'Ipv6Ranges': [
                            {
                                'CidrIpv6': cidr_ipv6,
                                'Description': 'Creted by moto'
                            },
                        ],
                        'ToPort': to_port
                    }
                ]

            )

# @mock_ec2
def main():
    ec2 = CustomEc2()

    ec2.create_sg('SG1', 0, 65535, '-1', '0.0.0.0/0', 'Public')
    ec2.create_sg('SG2', 0, 65535, '-1', '0.0.0.0/0', 'public')
    ec2.create_sg('SG3', 0, 65535, '-1', '0.0.0.0/0', 'private')
    ec2.create_sg('SG4', 0, 65535, '-1', '0.0.0.0/0', 'private', cidr_ipv6='::/0')
    ec2.create_sg('SG5', 0, 65535, '-1', '1.2.3.4/32', 'private')
    ec2.create_sg('SG6', 22, 22, 'tcp', '0.0.0.0/0', 'Public')
    ec2.create_sg('SG7', 22, 22, 'tcp', '0.0.0.0/0', 'public')
    ec2.create_sg('SG8', 22, 22, 'tcp', '0.0.0.0/0', 'private')
    ec2.create_sg('SG9', 22, 22, 'tcp', '1.2.3.4/32', 'private')
    ec2.create_sg('SG10', 22, 22, 'tcp', '0.0.0.0/0', 'private', cidr_ipv6='::/0')


if __name__ == "__main__":
    main()