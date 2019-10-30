import logging  
import boto3
import botocore
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)
exception_message = "Exception occured"
client = boto3.client("ec2")

WATCH_PORTS = [0, 22, 23, 125, 1433, 1434, 1521, 3306, 3389, 5432]
APPLICABLE_RESOURCES = ["AWS::EC2::SecurityGroup"]
COMPLIANT = "COMPLIANT"
NON_COMPLIANT = "NON_COMPLIANT"
NOT_APPLICABLE = "NOT_APPLICABLE"

def get_public_tagged_sgs(filter_name='tag:Confidentiality', filter_values=['Public']):  
    tagged_sg_ids = []
    response = client.describe_tags(

        Filters=[
            {
                'Name': filter_name,
                'Values': filter_values
            },
        ]
    )

    tags = response["Tags"]

    for tag in tags:
        resource_type = tag['ResourceType']
        resource_id = tag['ResourceId']

        if resource_type == 'security-group':
            tagged_sg_ids.append(resource_id)

    return tagged_sg_ids

def add_compliant_source(group_id, ip_protocol, from_port=0, to_port=65535):
    result = client.authorize_security_group_ingress(

        GroupId=group_id,
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
    print(f"Add rule result - {result}")

def remove_non_compliant(group_id, ip_protocol, cidr_ip, from_port=0, to_port=65535):
    print("Found Non Compliant IPV4 rule Security Group, GroupID - ", group_id)

    result = client.revoke_security_group_ingress(GroupId=group_id,
                                                    IpProtocol=ip_protocol,
                                                    CidrIp=cidr_ip,
                                                    FromPort=from_port,
                                                    ToPort=to_port)

    if result:
        compliance_type = COMPLIANT
    else:
        compliance_type = NON_COMPLIANT

    annotation_message = "Permissions were modified"

    return compliance_type, annotation_message

def remove_non_compliant_ipv6(group_id, ip_protocol, cidr_ip, from_port=0, to_port=65535):
    print("Found Non Compliant IPV6 rule Security Group, GroupID - ", group_id)
    
    result = client.revoke_security_group_ingress(GroupId=group_id,
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
        compliance_type = COMPLIANT
    else:
        compliance_type = NON_COMPLIANT

    annotation_message = "Permissions were modified"

    return compliance_type, annotation_message    

def evaluate_compliance(configuration_item):
    if configuration_item["resourceType"] not in APPLICABLE_RESOURCES:
        return {
            "compliance_type": "NOT_APPLICABLE",
            "annotation": "The rule doesn't apply to resources of type " +
                          configuration_item["resourceType"] + "."
        }

    if configuration_item["configurationItemStatus"] == "ResourceDeleted":
        return {
            "compliance_type": "NOT_APPLICABLE",
            "annotation": "The configurationItem was deleted and therefore cannot be validated."
        }

    group_id = configuration_item["configuration"]["groupId"]
    

    try:
        response = client.describe_security_groups(GroupIds=[group_id])
    except botocore.exceptions.ClientError as e:
        print(f"Botocore error - {e}")
        return {
            "compliance_type": NON_COMPLIANT,
            "annotation": "describe_security_groups failure on group " + group_id
        }
    
    compliance_type = COMPLIANT
    annotation_message = "Permissions are correct"

    public_tagged_sgs = get_public_tagged_sgs()
    if group_id not in public_tagged_sgs:
        # lets find public accessible CIDR Blocks
        for ip_permissions in response["SecurityGroups"][0]["IpPermissions"]:
            
            # if the rule is all protocol, FromPort is missing
            if "FromPort" not in ip_permissions:
                from_port = 0
                to_port = 65535
            else:
                from_port = ip_permissions["FromPort"]
                to_port = ip_permissions["ToPort"]

            protocol = ip_permissions["IpProtocol"]
            

            for ip_permission, rule in ip_permissions.items():
                if ip_permission == "IpRanges":
                    for cidr_block in rule:
                        cidr_ip = cidr_block["CidrIp"]

                        if cidr_ip == "0.0.0.0/0" and from_port in WATCH_PORTS:
                            compliance_type, annotation_message = remove_non_compliant(group_id,
                                                                    protocol,
                                                                    cidr_ip,
                                                                    from_port=from_port,
                                                                    to_port=to_port)
                            add_compliant_source(group_id, protocol, from_port=from_port, to_port=to_port)
                
                if ip_permission == "Ipv6Ranges" and rule:
                    for cidr_block in rule:
                        cidr_ip = cidr_block["CidrIpv6"]
                        if cidr_ip == "::/0" and from_port in WATCH_PORTS:
                            compliance_type, annotation_message = remove_non_compliant_ipv6(group_id,
                                                                    protocol,
                                                                    cidr_ip,
                                                                    from_port=from_port,
                                                                    to_port=to_port)
                else:
                    compliance_type = COMPLIANT
                    annotation_message = "Permissions are correct"
    return {
        "compliance_type": compliance_type,
        "annotation": annotation_message
    }


def lambda_handler(event, context):
    invoking_event = json.loads(event['invokingEvent'])
    configuration_item = invoking_event["configurationItem"]

    evaluation = evaluate_compliance(configuration_item)

    config = boto3.client('config')

    # the call to put_evalations is required to inform aws config about the changes
    response = config.put_evaluations(
        Evaluations=[
            {
                'ComplianceResourceType': invoking_event['configurationItem']['resourceType'],
                'ComplianceResourceId': invoking_event['configurationItem']['resourceId'],
                'ComplianceType': evaluation["compliance_type"],
                "Annotation": evaluation["annotation"],
                'OrderingTimestamp': invoking_event['configurationItem']['configurationItemCaptureTime']
            },
        ],
        ResultToken=event['resultToken'])

    print(f"Handler response - {response}")