#!/bin/bash

export stack_name="${1:-emr-roadshow}"

# 0. Setup AWS environment
echo "Setup AWS environment ..."
sudo yum -y install jq
export AWS_REGION=$(curl http://169.254.169.254/latest/meta-data/placement/region)
export ACCOUNT_ID=$(aws sts get-caller-identity --output text --query Account)

echo "export AWS_REGION=${AWS_REGION}" | tee -a ~/.bash_profile
echo "export ACCOUNT_ID=${ACCOUNT_ID}" | tee -a ~/.bash_profile
aws configure set default.region ${AWS_REGION}
aws configure get default.region

export S3BUCKET=$(aws cloudformation describe-stacks --stack-name $stack_name --query "Stacks[0].Outputs[?OutputKey=='CODEBUCKET'].OutputValue" --output text)
export MSK_SERVER=$(aws cloudformation describe-stacks --stack-name $stack_name --query "Stacks[0].Outputs[?OutputKey=='MSKBROKER'].OutputValue" --output text)
export VIRTUAL_CLUSTER_ID=$(aws cloudformation describe-stacks --stack-name $stack_name --query "Stacks[0].Outputs[?OutputKey=='VirtualClusterId'].OutputValue" --output text)
export EMR_ROLE_ARN=$(aws cloudformation describe-stacks --stack-name $stack_name --query "Stacks[0].Outputs[?OutputKey=='EMRExecRoleARN'].OutputValue" --output text)

echo "export S3BUCKET=${S3BUCKET}" | tee -a ~/.bash_profile
echo "export MSK_SERVER=${MSK_SERVER}" | tee -a ~/.bash_profile
echo "export VIRTUAL_CLUSTER_ID=${VIRTUAL_CLUSTER_ID}" | tee -a ~/.bash_profile
echo "export EMR_ROLE_ARN=${EMR_ROLE_ARN}" | tee -a ~/.bash_profile


# 1. setup Cloud9
echo "Configuring Cloud9 ..."
CLOUD9_INSTANCE_ID=$(aws ec2 describe-instances --filter Name=tag:aws:cloud9:environment,Values=$C9_PID --query Reservations[0].Instances[0].InstanceId --output text)
Cloud9AdminRole=$(aws iam list-roles --query 'Roles[?Description==`cloud9admin`].RoleName | [0]')
aws ec2 associate-iam-instance-profile --instance-id $CLOUD9_INSTANCE_ID --iam-instance-profile Name=$Cloud9AdminRole

curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
sudo ./aws/install --update
/usr/local/bin/aws cloud9 update-environment  --environment-id $C9_PID --managed-credentials-action DISABLE
rm -vf ${HOME}/.aws/credentials

# 2. install k8s command tools
echo "Installing kubectl tool..."
curl -O https://s3.us-west-2.amazonaws.com/amazon-eks/1.24.10/2023-01-30/bin/linux/amd64/kubectl
chmod +x kubectl
mkdir -p $HOME/bin && mv kubectl $HOME/bin/kubectl && export PATH=$PATH:$HOME/bin

# install eksctl
echo "Installing eksctl tool..."
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
eksctl version


# 3. install Kafka Client
echo "Installing Kafka Client tool ..."
wget https://archive.apache.org/dist/kafka/2.8.1/kafka_2.12-2.8.1.tgz
tar -xzf kafka_2.12-2.8.1.tgz
rm kafka_2.12-2.8.1.tgz

# 4. connect to the EKS newly created
echo $(aws cloudformation describe-stacks --stack-name $stack_name --query "Stacks[0].Outputs[?starts_with(OutputKey,'eksclusterEKSConfig')].OutputValue" --output text) | bash
echo "Testing EKS connection..."
kubectl get svc