import logging  
import boto3
import botocore
import json
from slack_alert import get_ssm_params, send_slack_message


logger = logging.getLogger()
logger.setLevel(logging.INFO)
exception_message = "Exception occured"

WATCH_PORTS = [0, 22, 23, 125, 1433, 1434, 1521, 3306, 3389, 5432]
APPLICABLE_RESOURCES = ["AWS::EC2::SecurityGroup"]
COMPLIANT = "COMPLIANT"
NON_COMPLIANT = "NON_COMPLIANT"
NOT_APPLICABLE = "NOT_APPLICABLE"


class Ec2Actions:
    def __init__(self, group_id='', time_stamp='', result_token =''):
        self.client = boto3.client("ec2")
        self.compliance_type = COMPLIANT
        self.annotation_message = "Permissions are correct"
        self.group_id = group_id
        self.time_stamp = time_stamp
        self.result_token = result_token

    def get_public_tags(self, filter_name='tag:Confidentiality', filter_values=['Public', 'public']):  
        response = self.client.describe_tags(

            Filters=[
                {
                    'Name': filter_name,
                    'Values': filter_values
                },
            ]
        )

        tags = response["Tags"]

        return tags

    def get_public_tagged_sgs(self):
        tagged_sg_ids = []

        tags = self.get_public_tags()
        for tag in tags:
            resource_type = tag['ResourceType']
            resource_id = tag['ResourceId']

            if resource_type == 'security-group':
                tagged_sg_ids.append(resource_id)

        return tagged_sg_ids

    def add_compliant_source(self, ip_protocol, from_port=0, to_port=65535):
        result = self.client.authorize_security_group_ingress(
            GroupId=self.group_id,
            IpPermissions=[
                {
                    'FromPort': from_port,
                    'IpProtocol': ip_protocol,
                    'IpRanges': [
                        {
                            'CidrIp': "10.0.0.0/8",
                            'Description': 'Updated by config because it was breaking compliance'
                        },
                    ],
                    'ToPort': to_port
                }
            ]

        )      
        print(f"Add rule result - {result['ResponseMetadata']['HTTPStatusCode']}")

    def remove_non_compliant_ingress(self, ip_protocol, cidr_ip, from_port=0, to_port=65535):
        try:
            print("Found Non Compliant IPV4 rule Security Group, GroupID - ", self.group_id)

            result = self.client.revoke_security_group_ingress(GroupId=self.group_id,
                                                            IpProtocol=ip_protocol,
                                                            CidrIp=cidr_ip,
                                                            FromPort=from_port,
                                                            ToPort=to_port)

            if result:
                self.compliance_type = COMPLIANT
            else:
                self.compliance_type = NON_COMPLIANT

            self.annotation_message = f"Permissions were modified - {self.compliance_type}"
        except:
            print(f"Ingress does not exists")

    def remove_non_compliant_ipv6_ingress(self, ip_protocol, cidr_ip, from_port=0, to_port=65535):
        print("Found Non Compliant IPV6 rule Security Group, GroupID - ", self.group_id)
        
        result = self.client.revoke_security_group_ingress(GroupId=self.group_id,
                    IpPermissions=[
                        {
                            'FromPort': from_port,
                            'IpProtocol': ip_protocol,
                            'Ipv6Ranges': [
                                {
                                    'CidrIpv6': cidr_ip
                                }
                            ],
                            'ToPort': to_port
                        }
                    ]
                )

        if result:
            self.compliance_type = COMPLIANT
        else:
            self.compliance_type = NON_COMPLIANT

        self.annotation_message = f"Permissions were modified - {self.compliance_type}" 

    def check_open_port_ingress_source(self, ip_permissions, protocol, from_port, to_port):
        for ip_permission, rule in ip_permissions.items():
            if ip_permission == "IpRanges":
                self.check_open_ipv4_ingress_source(rule, protocol, from_port, to_port)

            if ip_permission == "Ipv6Ranges" and rule:
                self.check_open_ipv6_ingress_source(rule, protocol, from_port, to_port)

    def check_open_ipv4_ingress_source(self, rule, protocol, from_port, to_port):  
        for cidr_block in rule:
            cidr_ip = cidr_block["CidrIp"]

            if cidr_ip == "0.0.0.0/0" and from_port in WATCH_PORTS:
                self.remove_non_compliant_ingress(protocol, cidr_ip, from_port=from_port, to_port=to_port)
                self.add_compliant_source(protocol, from_port=from_port, to_port=to_port) 

    def check_open_ipv6_ingress_source(self, rule, protocol, from_port, to_port):
        for cidr_block in rule:
            cidr_ip = cidr_block["CidrIpv6"]
            if cidr_ip == "::/0" and from_port in WATCH_PORTS:
                self.remove_non_compliant_ipv6_ingress(protocol, cidr_ip, from_port=from_port, to_port=to_port)                                                

    def evaluate_sg_ingress_ports(self, ip_permissions):
        for ip_permission in ip_permissions:            
            # if the rule is all protocol, FromPort is missing
            if "FromPort" not in ip_permission:
                from_port = 0
                to_port = 65535
            else:
                from_port = ip_permission["FromPort"]
                to_port = ip_permission["ToPort"]

            protocol = ip_permission["IpProtocol"]
            
            self.check_open_port_ingress_source(ip_permission, protocol, from_port, to_port)

    def evaluate_each_sg(self, public_tagged_sgs, security_groups):
        for security_group in security_groups:
            self.group_id = security_group['GroupId']
            ip_permission = security_group['IpPermissions']

            if self.group_id not in public_tagged_sgs:
                self.evaluate_sg_ingress_ports(ip_permission)
                self.set_config_evaluation()

    def set_config_evaluation(self):
        try:
            config = boto3.client('config')
            
            config.put_evaluations(
                Evaluations=[
                    {
                        'ComplianceResourceType': 'AWS::EC2::SecurityGroup',
                        'ComplianceResourceId': self.group_id,
                        'ComplianceType': self.compliance_type,
                        "Annotation": self.annotation_message,
                        'OrderingTimestamp': self.time_stamp
                    },
                ],
                ResultToken=self.result_token
            )
        except:
            print(f"{self.group_id} was not evaluated")
    
    def main(self):
        public_tagged_sgs = self.get_public_tagged_sgs()

        sg_description_response = self.client.describe_security_groups()
        security_groups = sg_description_response["SecurityGroups"]

        self.evaluate_each_sg(public_tagged_sgs, security_groups)

def lambda_handler(event, context):
    try:
        invoking_event = json.loads(event['invokingEvent'])
        time_stamp=invoking_event['notificationCreationTime']
        result_token=event['resultToken']

        Ec2Actions(time_stamp=time_stamp,result_token=result_token).main()
    except Exception:
        logger.exception(exception_message)
        error_webhook = get_ssm_params("SECURITY_ERRORS_SLACK")
        send_slack_message("Something went wrong, please check cloudwatch logstream", context=context, webhook_url=error_webhook)

    return "Lambda Finished"