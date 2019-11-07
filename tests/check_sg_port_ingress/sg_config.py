import boto3


class CustomSG:
    def __init__(self):
        self.client = boto3.client('ec2')

    def create_sg(self, group_name, from_port, to_port, ip_protocol, cidr_ip, tag, cidr_ipv6=False):
        sg_creation_response = self.client.create_security_group(
            Description='string',
            GroupName=group_name
        )
        group_id = sg_creation_response['GroupId']

        self.client.authorize_security_group_ingress(
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

        self.client.create_tags(
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
            self.client.authorize_security_group_ingress(
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

        return group_id

    def main(self):

        sg1 = self.create_sg('SG1', 0, 65535, '-1', '0.0.0.0/0', 'Public')
        sg2 = self.create_sg('SG2', 0, 65535, '-1', '0.0.0.0/0', 'public')
        sg6 = self.create_sg('SG6', 22, 22, 'tcp', '0.0.0.0/0', 'Public')
        sg7 = self.create_sg('SG7', 22, 22, 'tcp', '0.0.0.0/0', 'public')

        self.create_sg('SG3', 0, 65535, '-1', '0.0.0.0/0', 'private')
        self.create_sg('SG4', 0, 65535, '-1', '0.0.0.0/0', 'private', cidr_ipv6='::/0')
        self.create_sg('SG5', 0, 65535, '-1', '1.2.3.4/32', 'private')
        self.create_sg('SG8', 22, 22, 'tcp', '0.0.0.0/0', 'private')
        self.create_sg('SG9', 22, 22, 'tcp', '1.2.3.4/32', 'private')
        self.create_sg('SG10', 22, 22, 'tcp', '0.0.0.0/0', 'private', cidr_ipv6='::/0')

        public_sgs = [sg1, sg2, sg6, sg7] 

        return public_sgs