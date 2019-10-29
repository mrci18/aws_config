import logging  
import boto3
import botocore
import json
from slack_alert import get_ssm_params, send_slack_message

logger = logging.getLogger()
logger.setLevel(logging.INFO)
exception_message = "Exception occured"

COMPLIANT = "COMPLIANT"
NON_COMPLIANT = "NON_COMPLIANT"
NOT_APPLICABLE = "NOT_APPLICABLE"


class Ec2Actions:
    def __init__(self):
        self.client = boto3.client('ec2')

    def get_sg_ids(self):
        all_sg_ids = []
        response = self.client.describe_security_groups(
            MaxResults=500
        )
        security_groups = response['SecurityGroups']
        for security_group in security_groups:
            # group_name = security_group['GroupName']
            group_id = security_group['GroupId']
            all_sg_ids.append(group_id)

        return all_sg_ids

    def set_termination_tag(self, group_id, tag_value='True'):
        self.client.create_tags(
            Resources=[
                group_id,
            ],
            Tags=[
                {
                    'Key': 'Terminate',
                    'Value': tag_value
                },
            ]
        )

    def sg_id_is_unattached(self, filter_name: str, filter_value: str):
        response = self.client.describe_network_interfaces(
            Filters=[
                {
                    'Name': filter_name,
                    'Values': [filter_value],
                },
            ],
            MaxResults=500
        )

        if not response['NetworkInterfaces']:
            return True

    def get_network_interfaces(self, filter_value: list, filter_name='group-id'):
        response = self.client.describe_network_interfaces(
            Filters=[
                {
                    'Name': filter_name,
                    'Values': filter_value,
                },
            ],
            MaxResults=500
        )

        if response['NetworkInterfaces']:
            network_interfaces = response['NetworkInterfaces']
            return network_interfaces
        else:
            return
    def get_network_attached_sg_ids(self, filter_value: list, filter_name='group-id'):
        sg_ids_attached_to_network = set()
        network_interfaces = self.get_network_interfaces(filter_value)

        for network_interface in network_interfaces:
            groups = network_interface['Groups']
            for group in groups:
                attached_group_id = group['GroupId']
                sg_ids_attached_to_network.add(attached_group_id) 

        return sg_ids_attached_to_network

class LambdaActions:
    def __init__(self):
        self.client = boto3.client('lambda')

    
    def get_lambda_functions(self):
        response = self.client.list_functions()
        functions = response['Functions']

        return functions

    def get_sgs_attached_to_lambdas(self):
        sg_ids_attached_to_network_to_lambdas = []

        functions = self.get_lambda_functions()

        for function in functions:
            if 'VpcConfig' in function:
                sg_ids_attached_to_network_to_function = function['VpcConfig']['SecurityGroupIds']

                if sg_ids_attached_to_network_to_function and sg_ids_attached_to_network_to_function not in sg_ids_attached_to_network_to_lambdas:
                        sg_ids_attached_to_network_to_lambdas += sg_ids_attached_to_network_to_function

        # Removes duplicate sg ID's in list           
        sg_ids_attached_to_network_to_lambdas = list(dict.fromkeys(sg_ids_attached_to_network_to_lambdas))

        return sg_ids_attached_to_network_to_lambdas


def set_config_evaluation(resource_type, resource_id, compliance_type, annotation_message, time_stamp, result_token):
    config = boto3.client('config')
    
    config.put_evaluations(
        Evaluations=[
            {
                'ComplianceResourceType': resource_type,
                'ComplianceResourceId': resource_id,
                'ComplianceType': compliance_type,
                "Annotation": annotation_message,
                'OrderingTimestamp': time_stamp
            },
        ],
        ResultToken=result_token
    )

def lambda_handler(event, context):
    try:        
        invoking_event = json.loads(event['invokingEvent'])
        time_stamp=invoking_event['notificationCreationTime']
        result_token=event['resultToken']

        """Search for SG id's attached and set as compliant"""
        all_sg_ids = Ec2Actions().get_sg_ids()
        sg_ids_attached_to_network = Ec2Actions().get_network_attached_sg_ids(all_sg_ids)

        sgs_attached_to_lambda = LambdaActions().get_sgs_attached_to_lambdas()

        for sg_id in sgs_attached_to_lambda:
            sg_ids_attached_to_network.add(sg_id)

        for sg_id in sg_ids_attached_to_network:
            Ec2Actions().set_termination_tag(sg_id, tag_value='False')
            
            annotation_message = f"{sg_id} is currently attached to a resource"
            set_config_evaluation(
                resource_type='AWS::EC2::SecurityGroup', 
                resource_id=sg_id, 
                compliance_type=COMPLIANT, 
                annotation_message=annotation_message, 
                time_stamp=time_stamp,
                result_token=result_token
            )

        """Search for SG IDs unattached and set as non compliant"""
        for group_id in all_sg_ids:
            if Ec2Actions().sg_id_is_unattached('group-id', group_id) and group_id not in sgs_attached_to_lambda:

                Ec2Actions().set_termination_tag(group_id, tag_value='True')

                annotation_message = f"{group_id} is currently not attached to any resource, and was tagged for termination"
                set_config_evaluation(
                    resource_type='AWS::EC2::SecurityGroup', 
                    resource_id=group_id, 
                    compliance_type=NON_COMPLIANT, 
                    annotation_message=annotation_message, 
                    time_stamp=time_stamp,
                    result_token=result_token
                )
            
    except Exception:
        logger.exception(exception_message)
        error_webhook = get_ssm_params("SECURITY_ERRORS_SLACK")
        send_slack_message("Something went wrong, please check cloudwatch logstream", context=context, webhook_url=error_webhook)

    return "Lambda Finished"
