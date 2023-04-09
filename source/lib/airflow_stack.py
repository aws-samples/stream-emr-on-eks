# // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# // SPDX-License-Identifier: License :: OSI Approved :: MIT No Attribution License (MIT-0)
#
import os
from constructs import Construct
from aws_cdk import (CfnOutput, Aws, NestedStack, RemovalPolicy, Tags, CfnTag, aws_iam as iam, aws_mwaa as mwaa, aws_ec2 as ec2, aws_s3 as s3, aws_s3_deployment as s3deploy)

class AirflowStack(NestedStack):

    def __init__(self, scope: Construct, id: str, eksvpc: ec2.IVpc, env_name: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
    
        self.env_name = env_name

        self.airflow_bucket=s3.Bucket(self, "emr-serverless-airflow", 
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            removal_policy= RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        proj_dir=os.path.split(os.environ['VIRTUAL_ENV'])[0]
        self.deploy=s3deploy.BucketDeployment(self, "UploadRequirements",
            sources=[s3deploy.Source.asset(proj_dir+'/deployment/requirements')],
            destination_bucket= self.airflow_bucket,
            destination_key_prefix="requirements",
            memory_limit=256
        )

        self.bucket_name = self.airflow_bucket.bucket_name

        # Create MWAA role
        role = iam.Role(
            self,
            "EMR-Serverless-MWAARole",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("airflow.amazonaws.com"),
                iam.ServicePrincipal("airflow-env.amazonaws.com"),
            ),
        )
        role.add_to_policy(
            iam.PolicyStatement(
                resources=[
                    f"arn:aws:airflow:{self.region}:{self.account}:environment/{self.env_name}"
                ],
                actions=["airflow:PublishMetrics"],
                effect=iam.Effect.ALLOW,
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                resources=[
                    f"arn:aws:s3:::{self.bucket_name}",
                    f"arn:aws:s3:::{self.bucket_name}/*",
                ],
                actions=["s3:ListAllMyBuckets"],
                effect=iam.Effect.DENY,
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                resources=["*"],
                actions=["*"],
                effect=iam.Effect.ALLOW,
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:airflow-{self.env_name}-*"
                ],
                actions=[
                    "logs:CreateLogStream",
                    "logs:CreateLogGroup",
                    "logs:PutLogEvents",
                    "logs:GetLogEvents",
                    "logs:GetLogRecord",
                    "logs:GetLogGroupFields",
                    "logs:GetQueryResults",
                    "logs:DescribeLogGroups",
                ],
                effect=iam.Effect.ALLOW,
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                resources=["*"],
                actions=["cloudwatch:PutMetricData"],
                effect=iam.Effect.ALLOW,
            )
        )

        role.add_to_policy(
            iam.PolicyStatement(
                resources=["*"],
                actions=["sts:AssumeRole"],
                effect=iam.Effect.ALLOW,
            )
        )

        role.add_to_policy(
            iam.PolicyStatement(
                resources=[f"arn:aws:sqs:{self.region}:*:airflow-celery-*"],
                actions=[
                    "sqs:ChangeMessageVisibility",
                    "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes",
                    "sqs:GetQueueUrl",
                    "sqs:ReceiveMessage",
                    "sqs:SendMessage",
                ],
                effect=iam.Effect.ALLOW,
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "kms:Decrypt",
                    "kms:DescribeKey",
                    "kms:GenerateDataKey*",
                    "kms:Encrypt",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
                conditions={
                    "StringEquals": {
                        "kms:ViaService": [
                            f"sqs.{self.region}.amazonaws.com",
                            f"s3.{self.region}.amazonaws.com",
                        ]
                    }
                },
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "emr-serverless:CreateApplication",
                    "emr-serverless:GetApplication",
                    "emr-serverless:StartApplication",
                    "emr-serverless:StopApplication",
                    "emr-serverless:DeleteApplication",
                    "emr-serverless:StartJobRun",
                    "emr-serverless:GetJobRun"
                ],
                effect=iam.Effect.ALLOW,
                resources = ["*"],
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "iam:PassRole",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
                conditions={
                    "StringLike": {
                        "iam:PassedToService": "emr-serverless.amazonaws.com"
                    }
                },
            )
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ec2:DescribeInstances",
                    "ec2:CreateNetworkInterface",
                    "ec2:AttachNetworkInterface",
                    "ec2:DescribeNetworkInterfaces",
                    "autoscaling:CompleteLifecycleAction",
                    "ec2:DeleteNetworkInterface"
                ],
                effect=iam.Effect.ALLOW,
                resources = ["*"],
            )
        )

        # Create security group
        mwaa_sg = ec2.SecurityGroup(
            self,
            "SecurityGroup",
            vpc=eksvpc,
            description="Allow inbound access to MWAA",
            allow_all_outbound=True,
        )
        mwaa_sg.add_ingress_rule(
            mwaa_sg, ec2.Port.all_traffic(), "allow inbound access from the SG"
        )

        # Get private subnets
        subnet_ids = [subnet.subnet_id for subnet in eksvpc.private_subnets]
        
    

        mwaa_env = mwaa.CfnEnvironment(
            self,
            f"MWAAEnv{self.env_name}",
            name=self.env_name,
            dag_s3_path="dags",
            airflow_version="2.4.3",
            environment_class="mw1.small",
            max_workers=2,
            execution_role_arn=role.role_arn,
            logging_configuration=mwaa.CfnEnvironment.LoggingConfigurationProperty(
                dag_processing_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True, log_level="INFO"
                ),
                scheduler_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True, log_level="INFO"
                ),
                task_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True, log_level="INFO"
                ),
                webserver_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True, log_level="INFO"
                ),
                worker_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
                    enabled=True, log_level="INFO"
                ),
            ),
            network_configuration=mwaa.CfnEnvironment.NetworkConfigurationProperty(
                security_group_ids=[mwaa_sg.security_group_id], subnet_ids=subnet_ids
            ),
            requirements_s3_path="requirements/requirements.txt",
            source_bucket_arn=self.airflow_bucket.bucket_arn,
            webserver_access_mode="PUBLIC_ONLY",
        )
        mwaa_env.node.add_dependency(role)
        mwaa_env.node.add_dependency(self.deploy)
        CfnOutput(self, "MWAA_NAME", value=self.env_name)




    