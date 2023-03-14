# Workshop for EMR roadshow

This is a project developed in Python [CDK](https://docs.aws.amazon.com/cdk/latest/guide/home.html) for APAC EMR roadshow 2023.

The infrastructure deployment includes the following:
- A new S3 bucket to store sample data and stream job code
- An EKS cluster v1.24 in a new VPC across 2 AZs
    - The Cluster has 2 default managed node groups: the OnDemand nodegroup scales from 1 to 5, SPOT instance nodegroup can scale from 1 to 30. 
    - It also has a Fargate profile labelled with the value serverless
- An EMR virtual cluster in the same VPC
    - The virtual cluster links to `emr` namespace 
    - The namespace accommodates two types of Spark jobs, ie. run on managed node group or serverless job on Fargate
    - All EMR on EKS configuration are done, including fine-grained access controls for pods by the AWS native solution IAM roles for service accounts
- A MSK Cluster in the same VPC with 2 brokers in total. Kafka version is 2.8.1.
    - A Cloud9 IDE as the command line environment in the demo. 
    - Kafka Client tool will be installed on the Cloud9 IDE
- An EMR on EC2 cluster with managed scaling enabled.
    - 1 primary and 1 core nodes with r5.xlarge.
    - configured to run one Spark job at a time.
    - can scale from 1 to 10 core + task nodes
    - mounted EFS for checkpointing test/demo (a bootstrap action)

### CloudFormation Deployment

  |   Region  |   Launch Template |
  |  ---------------------------   |   -----------------------  |
  |  ---------------------------   |   -----------------------  |
  **US East (N. Virginia)**| [![Deploy to AWS](source/app_resources/00-deploy-to-aws.png)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/quickcreate?stackName=emr-roadshow&templateURL=https://blogpost-sparkoneks-us-east-1.s3.amazonaws.com/emr-stream-demo/workshop/emr-roadshow.template) 

* To launch in a different AWS Region, check out the following customization section, or use the CDK deployment option.

### Customization
You can customize the solution, such as set to a different region, then generate the CFN templates in your required region: 
```bash
export BUCKET_NAME_PREFIX=<my-bucket-name> # bucket where customized code will reside
export AWS_REGION=<your-region>
export SOLUTION_NAME=emr-stream-demo
export VERSION=workshop # version number for the customized code

./deployment/build-s3-dist.sh $BUCKET_NAME_PREFIX $SOLUTION_NAME $VERSION

# create the bucket where customized code will reside
aws s3 mb s3://$BUCKET_NAME_PREFIX-$AWS_REGION --region $AWS_REGION

# Upload deployment assets to the S3 bucket
aws s3 cp ./deployment/global-s3-assets/ s3://$BUCKET_NAME_PREFIX-$AWS_REGION/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control
aws s3 cp ./deployment/regional-s3-assets/ s3://$BUCKET_NAME_PREFIX-$AWS_REGION/$SOLUTION_NAME/$VERSION/ --recursive --acl bucket-owner-full-control

echo -e "\nIn web browser, paste the URL to launch the template: https://console.aws.amazon.com/cloudformation/home?region=$AWS_REGION#/stacks/quickcreate?stackName=emr-roadshow&templateURL=https://$BUCKET_NAME_PREFIX-$AWS_REGION.s3.amazonaws.com/$SOLUTION_NAME/$VERSION/emr-roadshow.template\n"
```

### CDK Deployment

#### Prerequisites 
Install the folowing tools:
1. [Python 3.6 +](https://www.python.org/downloads/).
2. [Node.js 10.3.0 +](https://nodejs.org/en/)
3. [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-macos.html#install-macosos-bundled). Configure the CLI by `aws configure`.
4. [CDK toolkit](https://cdkworkshop.com/15-prerequisites/500-toolkit.html)
5. [One-off CDK bootstrap](https://cdkworkshop.com/20-typescript/20-create-project/500-deploy.html) for the first time deployment.

#### Deploy
```bash
python3 -m venv .env
source .env/bin/activate
pip install -r requirements.txt

cdk deploy
```

## Post-deployment

The following `post-deployment.sh` is executable in Linux, not for Mac OSX. Modify the script if needed.

1. Open the "Kafka Client" IDE in Cloud9 console. Create one if the Cloud9 IDE doesn't exist. 
```
VPC prefix: 'emr-stream-demo'
Instance Type: 't3.small'
```
2. [Attach the IAM role that contains `Cloud9Admin` to your IDE](https://www.eksworkshop.com/020_prerequisites/ec2instance/). 

3. Turn off AWS managed temporary credentials in Cloud9:
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install --update
/usr/local/bin/aws cloud9 update-environment  --environment-id $C9_PID --managed-credentials-action DISABLE
rm -vf ${HOME}/.aws/credentials
```

4. Run the script to configure the cloud9 IDE environment:
```bash
curl https://raw.githubusercontent.com/aws-samples/stream-emr-on-eks/workshop/deployment/app_code/post-deployment.sh | bash
```
5. Wait for 5 mins, then check the [MSK cluster](https://console.aws.amazon.com/msk/) status. Make sure it is `active` before sending data to the cluster.
6. Launching a new termnial window in Cloud9, send the sample data to MSK:
```bash
wget https://github.com/xuite627/workshop_flink1015-1/raw/master/dataset/nycTaxiRides.gz
zcat nycTaxiRides.gz | split -l 10000 --filter="kafka_2.12-2.8.1/bin/kafka-console-producer.sh --broker-list ${MSK_SERVER} --topic taxirides ; sleep 0.2"  > /dev/null
```
6. Launching the 3rd termnial window and monitor the source MSK topic:
```bash
kafka_2.12-2.8.1/bin/kafka-console-consumer.sh \
--bootstrap-server ${MSK_SERVER} \
--topic taxirides \
--from-beginning
```

## Useful commands

 * `kubectl get pod -n emr`               list running Spark jobs
 * `kubectl delete pod --all -n emr`      delete all Spark jobs
 * `kubectl logs <pod name> -n emr`       check logs against a pod in the emr namespace
 * `kubectl get node --label-columns=eks.amazonaws.com/capacityType,topology.kubernetes.io/zone` check EKS compute capacity types and AZ distribution.


## Clean up
Run the clean-up script with:
```bash
curl https://raw.githubusercontent.com/aws-samples/stream-emr-on-eks/workshop/deployment/app_code/delete_all.sh | bash
```
Go to the [CloudFormation console](https://console.aws.amazon.com/cloudformation/home?region=us-east-1), manually delete the remaining resources if needed.
