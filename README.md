### AWSConfig

This repo contains AWS Config rules and lambdas for Matson. The lambdas associated with a Config rules is launched with the help of serverless framework(cloudformation under the hood)

# infra
infra directory contains cloudformation templates needed to support the deployment of the AWS Configs in an interable and secure manner 
  - infra/pipeline
    - s3 bucket where deployment artifacts are stored
    - 3 IAM roles, 1 for CodePipeline, CodeBuild, and DeployerRole(assumed by CodeBuild Role, used this way because we may transition to someday where role will be the only one reproduced in each account instead of the whole pipeline)
    - cloudwatch event that triggers lambda in ../monitoring directory, and will send out a slack message stating if build has succeeded or failed
    
# monitoring
monitoring directory contains a lambda and the role needed to run it, it is referenced by the cloudwatch event in infra directory and should also be used as reference when building future pipelines 

# check_sg_port_ingress
check_sg_port_ingress directory contains a lambda triggered once everyday to check if a security group ingress allows 0.0.0.0/0 or ::/0 from ports [0, 22, 23, 125, 1433, 1434, 1521, 3306, 3389, 5432]. If so, those ports will be reduce the source from 0.0.0.0/0 to 10.0.0.0/8. If we do want a security group to be excluded and allow ingress traffic from 0.0.0.0/0, all we need to do is tag that security group with a the key: "Confidentiality" and value: "Public".

# tag_for_termination
tag_for_termination directory contains 2 lambdas and a config rule. The first lambda (tag_sg_termination.py) that is attached to a scheduled config rule runs once a day. It will look for all security groups attached to a network interface, lambdas, cloudformation templates, and autoscaling groups. Any security groups that are not attached to a resource will be tagged for deletion. The second lambda is a lambda that runs on a scheduled cloudwatch event once a day. This will simply delete resources tagged for deletion 
