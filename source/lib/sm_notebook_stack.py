# // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# // SPDX-License-Identifier: License :: OSI Approved :: MIT No Attribution License (MIT-0)
#
from constructs import Construct
from aws_cdk import (Fn,NestedStack,aws_sagemaker as sm)
from aws_cdk.aws_iam import IRole 
from aws_cdk.aws_ec2 import (IVpc,SecurityGroup,Port)

class NotebookStack(NestedStack):

    def __init__(self, scope: Construct, id:str, livy_sg:str, eksvpc: IVpc, sagemaker_role:IRole, code_bucket:str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # setup env and download example notebook
        onCreateScript=f"""
        #!/bin/bash
        set -ex
        sudo -u ec2-user -i <<'EOF'

        export region=$(aws configure get region)
        export account_id=$(aws sts get-caller-identity --output text --query Account)
        export datalake_bucket=lf-datalake-$account_id-$region
        export engineer_role_arn=$(aws iam list-roles --query 'Roles[?contains(RoleName,`engineer`)].Arn' --output text)
        export analyst_role_arn=$(aws iam list-roles --query 'Roles[?contains(RoleName,`analyst`)].Arn' --output text)
        

        echo "export REGION=$region" | tee -a ~/.bash_profile
        echo "export ACCOUNTID=$account_id" | tee -a ~/.bash_profile
        echo "export DATALAKE_BUCKET=$datalake_bucket" | tee -a ~/.bash_profile
        echo "export CODE_BUCKET="{code_bucket} | tee -a ~/.bash_profile
        echo "export ENGINEER_ROLE=$engineer_role_arn" | tee -a ~/.bash_profile
        echo "export ANALYST_ROLE=$analyst_role_arn" | tee -a ~/.bash_profile
        
        aws s3 cp s3://{code_bucket}/app_code/job/EMR-lab-fine-grained-access-control.ipynb /home/ec2-user/SageMaker/
        aws s3 cp s3://{code_bucket}/app_code/job/emr-bootcamp-iceberg-db-creation.ipynb /home/ec2-user/SageMaker/
        aws s3 cp s3://{code_bucket}/app_code/job/emr-bootcamp-iceberg-table-read.ipynb /home/ec2-user/SageMaker/
        """

        sparkmagic_conf=sm.CfnNotebookInstanceLifecycleConfig(self, "oncreate_conf",
            notebook_instance_lifecycle_config_name="sparkmagic-config",
            on_create=[sm.CfnNotebookInstanceLifecycleConfig.NotebookInstanceLifecycleHookProperty(
                content=Fn.base64(onCreateScript)
            )])
        sm_sg=SecurityGroup.from_security_group_id(self, "notebook_sg", eksvpc.vpc_default_security_group,mutable=False)
        
        sm_notebook=sm.CfnNotebookInstance(self, "notebook", 
            notebook_instance_name="emr-runtime-lf-notebook",
            instance_type="ml.t3.medium",
            role_arn=sagemaker_role.role_arn,
            subnet_id=eksvpc.private_subnets[0].subnet_id,
            direct_internet_access="Disabled",
            security_group_ids=[sm_sg.security_group_id],
            volume_size_in_gb = 10,
            lifecycle_config_name="sparkmagic-config"
        )
        sm_notebook.add_dependency(sparkmagic_conf)

        # Allow Sagemaker notebook access Livy in EMR  
        self.emr_master_sg=SecurityGroup.from_security_group_id(self,"AdditionalSG",livy_sg)
        self.emr_master_sg.connections.allow_from(sm_sg, Port.tcp(8998), "open Livy port to SM")