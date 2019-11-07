#!/bin/bash

function deploy_kms(){
    echo -e "\n\nDeploying ${1}..."
    aws cloudformation deploy \
        --template-file ${2} \
        --stack-name ${1} \
        --parameter-overrides \
            Team=${team} User=${username}
}

function set_secure_ssm(){
    kmsID=$(aws cloudformation describe-stacks --stack-name ${3} --query "Stacks[].Outputs[].OutputValue[]" --output text | awk '{print $2}')
    echo -e "\nSetting SSM for ${1}"

    aws ssm put-parameter --cli-input-json '{"Type": "SecureString", "KeyId": "'"${kmsID}"'", "Name": "'"${1}"'", "Value": "'"${2}"'"}' --overwrite
}

# # Deploy S3 Pipeline Bucket
function deploy_pipeline_bucket(){
    aws cloudformation deploy \
        --no-fail-on-empty-changeset \
        --template-file ./infra/pipeline/bucket/PipelineBucket.yaml \
        --stack-name SecurityDeploymentBucket \
        --parameter-overrides \
            StageParameter=${stage}
}

# deploy PipelineRole
function deploy_pipeline_role(){
    echo -e "\n\nDeploying CodePipeline Role..."
    aws cloudformation deploy \
        --no-fail-on-empty-changeset \
        --template-file infra/pipeline/iam/CodePipelineRole.yaml \
        --stack-name CodePipelineRoleStack \
        --capabilities CAPABILITY_NAMED_IAM
}

# deploy CFT with no parameters
function deploy_regular_cft(){
    echo -e "\n\nDeploying ${1}..."
    aws cloudformation deploy \
        --no-fail-on-empty-changeset \
        --template-file ${2} \
        --stack-name ${1} \
        --capabilities CAPABILITY_NAMED_IAM
}

# Deploy Service Role
function deploy_service_deployer_role(){
    echo -e "\n\nDeploying ${service} Deployer Role..."
    aws cloudformation deploy \
        --no-fail-on-empty-changeset \
        --template-file infra/pipeline/iam/DeployerRole.yaml \
        --stack-name ${service}DeployerRoleStack \
        --parameter-overrides \
            Service=${service} \
            LService=${lservice} \
        --capabilities CAPABILITY_NAMED_IAM
}
# Deploy Pipeline
function deploy_pipeline(){
    echo -e "\n\nDeploying Pipeline..."
    aws cloudformation deploy \
        --no-fail-on-empty-changeset \
        --template-file infra/pipeline/Pipeline.yaml \
        --stack-name ${service}PipelineStack \
        --parameter-overrides \
            Service=${service} \
            Stage=${stage} \
            Team=${team} \
            BranchName=${branch} \
            RepositoryName=${repo} \
            GitHubOwner=${gitOwner} \
            GitHubSecret=${gitPassword} \
            GitHubOAuthToken=${oAuth} \
            BuildSpecPath=${buildspec} \
        --capabilities CAPABILITY_NAMED_IAM
    echo -e "\nCheck Codepipeline to view the status of deployment..."
    echo -e "Wait until script is fully finished executing..."
}

#Inputs
read -p "Stage/Account (e.g. mlscDev, mlscPreprod, mlscProd, mdaas, infosec, matsonlabs, qa, dr, org, china, workspaces, dev, pp, prod): " stage
read -p "AWS username running this script (e.g. bob@matson.com): " username

# Init config
service="AWSConfig"
lservice=${service,,} # Lowercase for S3 IAM permissions, bucket cannot be created if it has upper 
message="INFO: You are about to input sensitive data; your input will not be echo'd back to the terminal"
team="Security"

# Slack config
slack_error=$(echo SECURITY_ERRORS_SLACK)
echo -e "\n${message}"
read -sp "The webhook URL from slack for errors: " error_webhook

slack_deployment=$(echo SECURITY_DEPLOYMENT_SLACK)
echo -e "\n\n${message}"
read -sp "The webhook URL from slack for security deployment channel: " deployment_webhook

# For pipeline config
branch="master"
gitOwner="mrci18"
repo="aws_config"
buildspec="buildspec.yml"

echo -e "\n${message}"
read -sp "GitHub OAuth Token (Reference the doc link above if you need help): " oAuth

echo -e "\n\n${message}"
read -sp "Github password (i.e The GitHub account password that created the OAuthToken above): " gitPassword

### Main ###
deploy_kms AWSErrorKeyStack infra/kms/security_errors_key.yaml
deploy_kms SecurityDeploymentKeyStack infra/kms/security_deployment_key.yaml
set_secure_ssm  ${slack_error} ${error_webhook} AWSErrorKeyStack
set_secure_ssm  ${slack_deployment} ${deployment_webhook} SecurityDeploymentKeyStack
deploy_pipeline_bucket
deploy_regular_cft CodePipelineRoleStack infra/pipeline/iam/CodePipelineRole.yaml
deploy_regular_cft CodeBuildRoleStack infra/pipeline/iam/CodeBuildRole.yaml
deploy_regular_cft MonitorDeployerRoleStack monitoring/MonitorDeployerRole.yaml
deploy_service_deployer_role 
deploy_pipeline
# SLS deploy monitoring
# deploy cloudwatch event
# sls deploy tag for termination
# Deploy CFT template for config
