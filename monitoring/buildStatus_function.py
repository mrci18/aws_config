import logging
from slack_alert import send_slack_message, get_ssm_params

logger = logging.getLogger()
logger.setLevel(logging.INFO)

exception_message = "Exception occured"

def lambda_handler(event, context):
    try:
        print("Entering lambda_handler...")
        deployment_slack = get_ssm_params("SECURITY_DEPLOYMENT_SLACK")

        status = event["detail"]["build-status"]
        project = event["detail"]["project-name"]
        build = event["detail"]["build-id"]

        message = f">Project: `{project}`\n>BuildARN: `{build}`\n>Status: `{status}`"

        send_slack_message(message, context, webhook_url=deployment_slack)
        logger.info("Status: success")
    except Exception:
        logger.exception(exception_message)
