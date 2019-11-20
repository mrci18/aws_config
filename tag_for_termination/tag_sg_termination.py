import logging  
import boto3
import botocore
import json
import traceback
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

    def get_sgs_attached_to_cft(self, filter_name='tag:aws:cloudformation:stack-id', filter_values=['*']):  
        tags_attached_to_cft = []
        response = self.client.describe_tags(
            Filters=[
                {
                    'Name': filter_name,
                    'Values': filter_values
                },
            ]
        )

        tagged_resources = response["Tags"]
        for tagged_resource in tagged_resources:
            resource_type = tagged_resource['ResourceType']
            if resource_type == 'security-group':
                tags_attached_to_cft.append(tagged_resource['ResourceId'])

        return tags_attached_to_cft        
        # print(tags)

        # return tags

    def get_cft_attached_sgs(self):
    # def get_sg_tags(self):
        sgs_and_tags = {}
        response = self.client.describe_security_groups(
            MaxResults=500
        )
        security_groups = response['SecurityGroups']
        for security_group in security_groups:
            if 'Tags' in security_group.keys():

                group_id = security_group['GroupId']
                # print(group_id)
                tags = security_group['Tags']
                for tag in tags:
                    if 'aws:cloudformation:stack-id' in tag['Key']:
                        print(group_id)
                    # if 'aws:cloudformation:stack-id' in tag
                    # if 'aws:cloudformation:stack-id' in tag.keys():
                    #     print(group_id)
            # for tag in tags:
            #     print(tag)


        #     # group_name = security_group['GroupName']
        #     group_id = security_group['GroupId']
        #     all_sg_ids.append(group_id)

        # return all_sg_ids
    def set_termination_tag(self, group_id, tag_value='True'):
        try:
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
        except:
            print(traceback.format_exc())

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
    def get_network_attached_sg_ids(self, all_sg_ids=[], exception_list=[], filter_name='group-id'):
        sg_ids_attached_to_network = set()
        try:
            network_interfaces = self.get_network_interfaces(all_sg_ids)

            for network_interface in network_interfaces:
                groups = network_interface['Groups']
                for group in groups:
                    attached_group_id = group['GroupId']
                    sg_ids_attached_to_network.add(attached_group_id) 

            sg_ids_attached_to_network.union(exception_list)
        except:
            print(traceback.format_exc())

        return sg_ids_attached_to_network

class AutoScalingActions:
    def __init__(self):
        self.client = boto3.client('autoscaling')

    def get_sgs_attached_to_launch_configs(self):
        sgs_attached_to_launch_configs = []
        response = self.client.describe_launch_configurations(
            MaxRecords=100
        )

        launch_configs = response['LaunchConfigurations']
        for launch_config in launch_configs:
            if 'SecurityGroups' in launch_config:
                security_groups = launch_config['SecurityGroups']
                sgs_attached_to_launch_configs += security_groups

        return sgs_attached_to_launch_configs

class LambdaActions:
    def __init__(self):
        self.client = boto3.client('lambda')

    
    def get_lambda_functions(self):
        response = self.client.list_functions()
        functions = response['Functions']

        return functions

    def get_sgs_attached_to_lambdas(self):
        sg_ids_attached_to_network_to_lambdas = []

        try:

            functions = self.get_lambda_functions()

            for function in functions:
                if 'VpcConfig' in function:
                    sg_ids_attached_to_network_to_function = function['VpcConfig']['SecurityGroupIds']

                    if sg_ids_attached_to_network_to_function and sg_ids_attached_to_network_to_function not in sg_ids_attached_to_network_to_lambdas:
                            sg_ids_attached_to_network_to_lambdas += sg_ids_attached_to_network_to_function

            # Removes duplicate sg ID's in list           
            sg_ids_attached_to_network_to_lambdas = list(dict.fromkeys(sg_ids_attached_to_network_to_lambdas))
        except:
            print(traceback.format_exc())

        return sg_ids_attached_to_network_to_lambdas


def set_config_evaluation(resource_type, resource_id, compliance_type, annotation_message, time_stamp, result_token):
    try:
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
    except:
        print(f"{resource_id} was not evaluated")

def set_attached_sgs_compliance_and_tag(sg_ids_attached_to_network, time_stamp, result_token):
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

def set_unattached_sgs_non_compliance_and_tag(all_sg_ids, combined_exception_list, time_stamp, result_token):
    # Best way I could think of to retrieve SGs that ARE NOT attached to network interface
    for group_id in all_sg_ids:
        if Ec2Actions().sg_id_is_unattached('group-id', group_id) and group_id not in combined_exception_list:

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

def combine_exception_list_sgs(sgs_attached_to_lambda, sgs_attached_to_cft, sgs_attached_to_launch_configs):
    exception_list = set()
    for sg_id in sgs_attached_to_lambda:
        exception_list.add(sg_id)

    for sg_id in sgs_attached_to_cft:
        exception_list.add(sg_id)

    for sg_id in sgs_attached_to_launch_configs:
        exception_list.add(sg_id)

    return exception_list

def lambda_handler(event, context):
    try:        
        invoking_event = json.loads(event['invokingEvent'])
        time_stamp=invoking_event['notificationCreationTime']
        result_token=event['resultToken']

        """Search for SG ID's"""
        all_sg_ids = Ec2Actions().get_sg_ids()
        sgs_attached_to_lambda = LambdaActions().get_sgs_attached_to_lambdas()
        sgs_attached_to_cft = Ec2Actions().get_sgs_attached_to_cft()
        sgs_attached_to_launch_configs = AutoScalingActions().get_sgs_attached_to_launch_configs()

        combined_exception_list = combine_exception_list_sgs(sgs_attached_to_lambda, sgs_attached_to_cft, sgs_attached_to_launch_configs)
        sg_ids_attached_to_network = Ec2Actions().get_network_attached_sg_ids(all_sg_ids=all_sg_ids, exception_list=combined_exception_list)
        
        """Set Compliance"""
        set_attached_sgs_compliance_and_tag(sg_ids_attached_to_network, time_stamp, result_token)

        set_unattached_sgs_non_compliance_and_tag(all_sg_ids, combined_exception_list, time_stamp, result_token)

    except Exception:
        logger.exception(exception_message)
        error_webhook = get_ssm_params("SECURITY_ERRORS_SLACK")
        send_slack_message("Something went wrong, please check cloudwatch logstream", context=context, webhook_url=error_webhook)

    return "Lambda Finished"

if __name__ == "__main__":
    # AutoScalingActions().get_sgs_attached_to_launch_configs()
    x = set()
    y = set()

    x.add(1)
    x.add(22)
    y.add(1)
    y.add(3)

    x.union(y)

    print(x)
    # print(sg_ids)
