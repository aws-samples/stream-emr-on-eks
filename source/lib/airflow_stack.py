# // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# // SPDX-License-Identifier: License :: OSI Approved :: MIT No Attribution License (MIT-0)
#
import os
from constructs import Construct
from aws_cdk import (CfnOutput, Aws, NestedStack, RemovalPolicy, Tags, CfnTag, aws_iam as iam, aws_mwaa as mwaa, aws_ec2 as ec2, aws_s3 as s3, aws_s3_deployment as s3deploy)
from lib.util.manifest_reader import load_yaml_replace_var_local

class AirflowStack(NestedStack):

    @property
    def mwaa_name(self):
        return self.env_name

    @property
    def mwaa_s3bucket(self):
        return self.airflow_bucket.bucket_name

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
        self.upload_req=s3deploy.BucketDeployment(self, "UploadRequirements",
            sources=[s3deploy.Source.asset(proj_dir+'/deployment/requirements')],
            destination_bucket= self.airflow_bucket,
            destination_key_prefix="requirements"
            # memory_limit=256
        )
        self.bucket_name = self.airflow_bucket.bucket_name

        # Create MWAA role
        _mwaa_role = iam.Role(self,"EMR-Serverless-MWAARole",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("airflow.amazonaws.com"),
                iam.ServicePrincipal("airflow-env.amazonaws.com")
            )
        )

        source_dir=os.path.split(os.environ['VIRTUAL_ENV'])[0]+'/source'
        _iam = load_yaml_replace_var_local(source_dir+'/app_resources/airflow-iam-role.yaml', 
            fields= {
                "{{codeBucket}}": self.bucket_name,
                "{{AccountID}}": Aws.ACCOUNT_ID,
                "{{REGION}}": Aws.REGION,
                "{{env_name}}": self.env_name
            })
        for statmnt in _iam:
            _mwaa_role.add_to_policy(iam.PolicyStatement.from_json(statmnt)
        )

        # Create security group
        mwaa_sg = ec2.SecurityGroup(self,"SecurityGroup",
            vpc=eksvpc,
            description="Allow inbound access to MWAA",
            allow_all_outbound=True,
        )
        mwaa_sg.add_ingress_rule(mwaa_sg, ec2.Port.all_traffic(), "allow inbound access from the SG"
        )

        # Get private subnets
        subnet_ids = [subnet.subnet_id for subnet in eksvpc.private_subnets]
    
        mwaa_env = mwaa.CfnEnvironment(self,f"MWAAEnv{self.env_name}",
            name=self.env_name,
            dag_s3_path="dags",
            airflow_version="2.4.3",
            environment_class="mw1.small",
            max_workers=2,
            execution_role_arn=_mwaa_role.role_arn,
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
                security_group_ids=[mwaa_sg.security_group_id], 
                subnet_ids=subnet_ids
            ),
            requirements_s3_path="requirements/requirements.txt",
            source_bucket_arn=self.airflow_bucket.bucket_arn,
            webserver_access_mode="PUBLIC_ONLY",
        )
        mwaa_env.node.add_dependency(_mwaa_role)
        mwaa_env.node.add_dependency(self.upload_req)
        mwaa_env.apply_removal_policy(RemovalPolicy.DESTROY)

    