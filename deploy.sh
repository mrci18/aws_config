#!/bin/bash
# serviceName="config"
# read -p "Enter stage: " stage

# export SERVICE=${serviceName}
# export ACCOUNT_ALIAS=$(aws iam list-account-aliases --query "AccountAliases[]" --output text)
# export ACCOUNT_ID=$(aws sts get-caller-identity --output text --query 'Account')

# "C:\Users\cibo\AppData\Roaming\npm\serverless" deploy --stage ${stage}

# aws cloudformation deploy \
#     --template-file ./config.yaml \
#     --stack-name ${serviceName}TagSgStack

#Create KMS key for SECURITY_DEPLOYMENT_SLACK SSM 
#Create KMS key for SECURITY_ERRORS_SLACK SSM


#Set SSM Paramter for aws-erros webhook as SECURITY_ERRORS_SLACK
#Set SSM Paramtere for security-deployments webhook SECURITY_DEPLOYMENT_SLACK



#Inputs
# read -p "Stage/Account (e.g. mlscDev, mlscPreprod, mlscProd, mdaas, infosec, matsonlabs, qa, dr, org, china, workspaces, dev, pp, prod): " stage

# Init config
service="AWSConfig"
lservice=${service,,}
message="INFO: You are about to input sensitive data; your input will not be echo'd back to the terminal"
team="Security"

# For pipeline config
branch="master"
gitOwner="mrci18"
repo="aws_config"
buildspec="buildspec.yml"

read -p "Stage/Account (e.g. mlscDev, mlscPreprod, mlscProd, mdaas, infosec, matsonlabs, qa, dr, org, china, workspaces, dev, pp, prod): " stage

echo -e "\n${message}"
read -sp "GitHub OAuth Token (Reference the doc link above if you need help): " oAuth

echo -e "\n\n${message}"
read -sp "Github password (i.e The GitHub account password that created the OAuthToken above): " gitPassword

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
        --stack-name ${service}DeployerStack \
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

### Main ###
# Place keys in this directory
deploy_kms AWSErrorKey ./security_errors_key.yaml
deploy_kms SecurityDeploymentKey ./security_deployment_key.yaml
deploy_pipeline_bucket
deploy_regular_cft CodePipelineRoleStack infra/pipeline/iam/CodePipelineRole.yaml
deploy_regular_cft CodeBuildRoleStack infra/pipeline/iam/CodeBuildRole.yaml
deploy_regular_cft MonitorDeployerStack monitoring/MonitorDeployerRole.yaml
# deploy_service_deployer_role 
# deploy_pipeline
# SLS deploy monitoring
# deploy cloudwatch event
# sls deploy tag for termination
# Deploy CFT template for config
