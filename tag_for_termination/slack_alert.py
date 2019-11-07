from urllib import request
import json
import logging
import boto3
import os
import hmac
import hashlib

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_ssm_params(ssm_param):
    logger.info(f"SSMParam: {ssm_param}")
    ssm = boto3.client('ssm')
    response = ssm.get_parameters(
        Names=[ssm_param],WithDecryption=True
    )
    for parameter in response['Parameters']:
        return parameter['Value']

def send_slack_message(message, context = None, webhook_url = ""):
    print("Sending slack message...")
    if context:
        account_alias = os.environ["ACCOUNT_ALIAS"]
        region = os.environ["REGION"]

        combined_message = f"*Lambda Function:* `{context.function_name}`\n*Account:* `{account_alias}`\n*Region:* `{region}`\n*Log Stream:* `{context.log_stream_name}`\n\n{message}"
        data = {
            "text": combined_message,
            "color": "#7CD197"
        }

        json_data = json.dumps(data)

        req = request.Request(webhook_url, data=json_data.encode('ascii'), headers={'Content-Type': 'application/json'})
        resp = request.urlopen(req)

        logger.info(f"SlackRequest: {resp.getcode()}")