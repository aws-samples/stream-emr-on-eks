# Workshop for EMR roadshow

This is a project developed in Python [CDK](https://docs.aws.amazon.com/cdk/latest/guide/home.html) for APAC EMR roadshow 2023.

The infrastructure deployment includes the following:
- A new S3 bucket for applications
    - encrypted by KMS_MANAGED key
    - auto-upload files from ./deployment/app_code
- A new DataLake S3 bucket
    - encrypted by KMS_MANAGED key
    - registered in Lakeformation as a data lake
    - naming convention is s3://lf-datalake-{Aws.ACCOUNT_ID}-{Aws.REGION}
- A new S3 bucket for Amazon Managed Workflows for Apache Airflow (MWAA) 
    - auto-upload files from ./deployment/requirements/
    - used for MAAA DAGs
    - naming converion is s3://emr-roadshow-airflowstac-emrserverlessairflow*
- A MWAA Environment
    - install `apache-airflow-providers-amazon` pip package for EMR Serverless operator
    - `*EMR-Serverless-MWAARole*` IAM role for MAWW environment
- An EKS cluster v1.24 in a new VPC across 2 AZs
    - The Cluster has 2 default managed node groups: the OnDemand nodegroup scales from 1 to 5, SPOT instance nodegroup can scale from 1 to 30. 
    - It also has a Fargate profile labelled with the value serverless
- An EMR virtual cluster in the same VPC
    - The virtual cluster links to `emr` namespace 
    - The namespace accommodates two types of Spark jobs, ie. run on managed node group or serverless job on Fargate
    - All EMR on EKS configuration are done, including fine-grained access controls for pods by the AWS native solution IAM roles for service accounts
- A Cloud9 IDE in the same VPC
    - automatically stop in 5 mins
- An EMR on EC2 cluster.
    - 1 primary and 1 core nodes with r5.xlarge
    - configured to run one Spark job at a time.
    - managed scaling is enabled, can scale from 1 to 10
    - mounted EFS for checkpointing test/demo via a bootstrap action
- A Sagemaker notebook
    - lf-sagemaker-role: SageMaker notebook instance role with support of EMR runtime role
    - an instance of notebook with 10GB of volume in a private subnet
    - no direct internet access
- Two EMR runtime roles
    - lf-data-access-engineer: the runtime role with LakeFormation data access permission designed for *Data Engineers* who can create DB and tables etc.
    - lf-data-access-analyst: the runtime role with LakeFormation data access permission designed for *Data Analyst* who have tag-based LF read-only permission
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
2. [Attach the `Cloud9Admin` IAM role to your Cloud9 IDE](https://www.eksworkshop.com/020_prerequisites/ec2instance/). 

3. Run the command to turn off the AWS managed temporary credentials in Cloud9:
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install --update
/usr/local/bin/aws cloud9 update-environment  --environment-id $C9_PID --managed-credentials-action DISABLE
rm -vf ${HOME}/.aws/credentials
```

4. Setup the connection to MSK & EKS in Cloud9:
```bash
curl https://raw.githubusercontent.com/aws-samples/stream-emr-on-eks/workshop/deployment/app_code/post-deployment.sh | bash
```
5. Wait for 5 mins, then check the [MSK cluster](https://console.aws.amazon.com/msk/) status. Make sure it is `active` before sending data to the cluster.
6. Launching a new termnial window in Cloud9, send the sample data to MSK:
```bash
wget https://github.com/xuite627/workshop_flink1015-1/raw/master/dataset/nycTaxiRides.gz
zcat nycTaxiRides.gz | split -l 10000 --filter="kafka_2.12-2.8.1/bin/kafka-console-producer.sh --broker-list ${MSK_SERVER} --topic taxirides ; sleep 0.2"  > /dev/null
```
6. Launching the 2nd termnial window and monitor the source MSK topic in Cloud9:
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
