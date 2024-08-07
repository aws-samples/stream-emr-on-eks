#!/bin/bash

export stack_name="${1:-emr-stream-demo}"

# 0. Setup AWS environment
echo "Setup AWS environment ..."
# sudo yum -y install jq
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
export EKS_CLUSTER_NAME=$(aws cloudformation describe-stacks --stack-name $stack_name --query "Stacks[0].Outputs[?contains(OutputKey, 'EKSClusterName')].OutputValue" --output text)

echo "export S3BUCKET=${S3BUCKET}" | tee -a ~/.bash_profile
echo "export MSK_SERVER=${MSK_SERVER}" | tee -a ~/.bash_profile
echo "export VIRTUAL_CLUSTER_ID=${VIRTUAL_CLUSTER_ID}" | tee -a ~/.bash_profile
echo "export EMR_ROLE_ARN=${EMR_ROLE_ARN}" | tee -a ~/.bash_profile
echo "export EKS_CLUSTER_NAME=${EKS_CLUSTER_NAME}" | tee -a ~/.bash_profile
source ~/.bash_profile

# 1. install k8s command tools
echo "Installing kubectl tool..."
curl -O https://s3.us-west-2.amazonaws.com/amazon-eks/1.28.5/2024-01-04/bin/linux/amd64/kubectl
chmod +x kubectl
mkdir -p $HOME/bin && mv kubectl $HOME/bin/kubectl && export PATH=$PATH:$HOME/bin

# install eksctl
echo "Installing eksctl tool..."
curl --silent --location "https://github.com/weaveworks/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
eksctl version

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash

# # 2. Update MSK with custom configuration
# base64 <<EoF >msk-config.txt
# auto.create.topics.enable=true
# log.retention.minutes=1440
# zookeeper.connection.timeout.ms=1000
# log.roll.ms=60480000
# EoF

# validate=$(aws kafka list-configurations --query 'Configurations[?Name==`autotopic`].Arn' --output text)
# if [ -z "$validate" ]; then
#     echo "Update MSK configuration ..."

#     configArn=$(aws kafka create-configuration --name "autotopic" --description "Topic autocreation enabled; Log retention 24h; Apache ZooKeeper timeout 1000 ms; Log rolling 16h." --server-properties file://msk-config.txt | jq -r '.Arn')
#     msk_cluster=$(aws kafka list-clusters --region $AWS_REGION --query 'ClusterInfoList[?ClusterName==`'$stack_name'`].ClusterArn' --output text)
#     msk_version=$(aws kafka describe-cluster --cluster-arn ${msk_cluster} --query "ClusterInfo.CurrentVersion" --output text)
#     aws kafka update-cluster-configuration --cluster-arn ${msk_cluster} --configuration-info '{"Arn": "'$configArn'","Revision": 1 }' --current-version ${msk_version}
# fi

# 2. install Kafka Client
echo "Installing Kafka Client tool ..."
wget https://archive.apache.org/dist/kafka/2.8.1/kafka_2.12-2.8.1.tgz
tar -xzf kafka_2.12-2.8.1.tgz
rm kafka_2.12-2.8.1.tgz

# 3. connect to the EKS newly created
echo $(aws cloudformation describe-stacks --stack-name $stack_name --query "Stacks[0].Outputs[?starts_with(OutputKey,'eksclusterEKSConfig')].OutputValue" --output text) | bash
echo "Testing EKS connection..."
kubectl get svc

# 4. install EBS CSI driver
eksctl create iamserviceaccount \
  --name ebs-csi-controller-sa \
  --namespace kube-system \
  --cluster $EKS_CLUSTER_NAME \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
  --approve \
  --role-only \
  --role-name AmazonEKS_EBS_CSI_DriverRole

eksctl create addon --name aws-ebs-csi-driver --cluster $EKS_CLUSTER_NAME --service-account-role-arn arn:aws:iam::$ACCOUNT_ID:role/AmazonEKS_EBS_CSI_DriverRole --force --region $AWS_REGION