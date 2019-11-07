import sys
sys.path.append("../")
sys.path.append("../../tag_for_termination/")
import boto3
from moto import mock_ec2
import unittest
from ec2_config import CustomEC2
from tag_sg_termination import lambda_handler

event = {'version': '1.0', 'invokingEvent': '{"awsAccountId":"123456789012","notificationCreationTime":"2019-11-07T01:30:33.721Z","messageType":"ScheduledNotification","recordVersion":"1.0"}', 'resultToken': 'eyJlbmNyeXB0ZWREYXRhIjpbLTI4LC0zNiwxMTMsLTM0LC02NSwtMTE1LDE1LC0xMTgsLTQ0LC05MCw1LDksNTYsLTUyLDEyNywtNzMsLTg0LC03NywxNSw0LDEyNywtMjksMzIsMjIsODYsNDQsLTc3LDI4LC02OCwxMTksLTIwLC03MCw1MywtODcsLTIwLC04OCwtMTgsNzgsLTc1LC01OCwtMTAwLC0zNSwyMCwtNTEsMTAzLC0xMTQsLTQ5LC0xMjQsODYsNzksNjUsLTcxLDU5LDM4LDEwMywtODEsLTEyMyw5NCwxNiwtNzAsMTksLTUzLC01NCwtMTE1LC02OCw5NiwzOSwtMTE2LC0xMywtNjcsLTE3LC0zNSwtNDUsMjksMTEsLTEyMiw3MCwtNjEsODQsLTI0LDY1LDI0LDMwLDU3LC01OCwxMDUsLTU4LDg4LDI0LC0xMjYsNTksNCw4OCwtMywxMywtMTUsMjcsLTI4LDEyNSwzMiwtMTAwLDUsLTIxLDg2LDExOCw0LC0xOSwzNCwtNTIsODAsMjUsNDUsNywtNDQsMzAsNjQsMjYsLTY5LC0yNSw0NSwtNTAsOTgsNjUsNDAsLTc4LDk5LC0xMDEsMTIxLDEyMiwtMTA3LDg0LDExMSwtODcsLTgzLC00MCw4Myw2MSwyOCwyMiw4MSwtNDUsMTcsMjMsNzgsLTk3LDM3LC0xMjEsNjcsMTIyLDE3LC03MSwzMSwzMiwxMDIsLTI1LC01MiwtMjgsMzcsMzUsMTExLC05Miw5MSwzNSw3MSwyMiwyOSwyMCwtMTIyLDg2LC01OSwzMywtMTA3LC02NSwxMDksMSw1OCwxMjAsMTA3LDEwOCw5Nyw0OSwtMTA0LDE1LDk0LDExMywtMTA2LC0xMDMsLTc5LDEwMiwtMTcsLTMxLDg2LC01NSw1NCwtMjcsMTUsLTEsNTQsLTMsMjksMTA3LC0yLDEwMywtMTEsLTQ4LDc2LDQwLDExNSw2Myw2NCw3OSwtOTgsNTUsMzcsOTAsODQsMzgsMTEyLDg4LC05MiwtMTAzLDEyNCw2LC0xMTAsLTEwOCw2NywtMTksLTY2LDg2LC01OCw1NywtMTcsODgsLTY4LC0zMywtODAsLTQ0LC0xMDgsLTQ1LDg4LC05LC03OCwtNTMsNTgsMjAsLTExNSwtMTE5LC04OCwxMDAsLTEyMCw0NiwtMTIzLDIyLC02LC04Nyw0MSwxMjEsODEsLTk1LC02OSwtMTE0LDg1LDQwLDI5LC0xNiwtNjYsMTAyLC05LDgwLDExMSwxMjEsMjUsLTY2LC02MCwxMTksOTEsLTI2LC0xMTIsNjksLTExMiwtNDMsLTY2LC0xLDEyMSwtMzEsNjYsNzYsLTExNiw4NiwtNzksMTI2LC0xMTAsLTgyLC05NCw4MCwxMCwzNiwtMTcsNzUsLTU2LDUsLTI4LDEwNSwtOTEsNzcsLTYzLC0zOCwxMDQsMjcsLTU3LC0xMjgsLTU1LDg1LC0xMDgsLTMyLDc3LC0zNCwtMTEwLDYsLTQ0LDI5LDgzLDE5LC0xMjAsLTEyMSwtMTAwLDM0LC00NywtMjMsLTI0LDgsLTQyLC0xMTksMTE2LC0xMjMsNzEsLTEwLDk2LC00NiwtMTIsLTc3LDcyXSwibWF0ZXJpYWxTZXRTZXJpYWxOdW1iZXIiOjEsIml2UGFyYW1ldGVyU3BlYyI6eyJpdiI6WzM5LDAsMTA1LDEyMCwtNjgsMCwxNCwtODIsODAsLTc2LDEwNywtMTA5LDE2LC00NywtNTMsLTYxXX19', 'eventLeftScope': False, 'executionRoleArn': 'arn:aws:iam::123456789012:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig', 'configRuleArn': 'arn:aws:config:us-west-2:123456789012:config-rule/config-rule-f4mdge', 'configRuleName': 'AWSConfigCheckSGPortIngress', 'configRuleId': 'config-rule-f4mdge', 'accountId': '123456789012'}


@mock_ec2
def setUpModule():
    CustomEC2().main()
    lambda_handler(event, '')

@mock_ec2
class CustomEc2SG(unittest.TestCase):
    def test_out(self):
        client = boto3.client('ec2')
        response = client.describe_security_groups()
        security_groups = response['SecurityGroups']
        for security_group in security_groups:
            terminate_tag = security_group['Tags']
            print(terminate_tag)