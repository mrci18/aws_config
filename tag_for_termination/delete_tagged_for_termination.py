import logging
import boto3
from botocore.exceptions import ClientError
from slack_alert import get_ssm_params, send_slack_message

logger = logging.getLogger()
logger.setLevel(logging.INFO)
exception_message = "Exception occured"

class Ec2Actions:
    def __init__(self):
        self.client = boto3.client('ec2')

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

    def delete_security_group(self, resource_id: str):
        try:
            self.client.delete_security_group(GroupId=resource_id)

            print(f"{resource_id} has been deleted")
        except ClientError as e:
            self.set_termination_tag(resource_id, tag_value='False')
            print(f"Error - {e}")

    def describe_tags_for_termination(self, filter_name='tag:Terminate', filter_values=['True']):  
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

    def get_sgs_tagged_for_termination(self):
        sg_ids_tagged_for_termination = []

        tags = self.describe_tags_for_termination()

        for tag in tags:
            resource_type = tag['ResourceType']
            resource_id = tag['ResourceId']

            if resource_type == 'security-group':
                sg_ids_tagged_for_termination.append(resource_id)

        return sg_ids_tagged_for_termination

class LambdaActions:
    def __init__(self):
        self.client = boto3.client('lambda')

    
    def get_lambda_functions(self):
        response = self.client.list_functions()
        functions = response['Functions']

        return functions

    def get_sgs_attached_to_lambdas(self):
        sg_ids_attached_to_lambdas = []

        functions = self.get_lambda_functions()

        for function in functions:
            if 'VpcConfig' in function:
                sg_ids_attached_to_function = function['VpcConfig']['SecurityGroupIds']

                if sg_ids_attached_to_function and sg_ids_attached_to_function not in sg_ids_attached_to_lambdas:
                        sg_ids_attached_to_lambdas += sg_ids_attached_to_function

        # Removes duplicate sg ID's in list           
        sg_ids_attached_to_lambdas = list(dict.fromkeys(sg_ids_attached_to_lambdas))

        return sg_ids_attached_to_lambdas

def lambda_handler(event, context):
    try:
        ec2 = Ec2Actions()
        sgs_to_delete = ec2.get_sgs_tagged_for_termination()
        
        for sg in sgs_to_delete:
            ec2.delete_security_group(sg)

    except Exception:
        logger.exception(exception_message)
        error_webhook = get_ssm_params("SECURITY_ERRORS_SLACK")
        send_slack_message("Something went wrong, please check cloudwatch logstream", context=context, webhook_url=error_webhook)

    return "Lambda Finished"
    