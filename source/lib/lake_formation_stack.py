# // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# // SPDX-License-Identifier: License :: OSI Approved :: MIT No Attribution License (MIT-0)
#
from constructs import Construct
from aws_cdk import (Fn,Aws,NestedStack,RemovalPolicy,aws_s3 as s3,aws_iam as iam,aws_lakeformation as lf)


class LFStack(NestedStack):

    def __init__(self, scope: Construct, id: str, engineer_role: iam.IRole, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

       
        # Create an empty datalake S3 bucket
        self.lf_bucket=s3.Bucket(self, "LFbucket", 
            bucket_name=f"lf-datalake-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            removal_policy= RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        #register it as data lake location
        lf.CfnResource(self, "DLLoation",
            resource_arn=self.lf_bucket.bucket_arn,
            use_service_linked_role=False,
            role_arn=engineer_role.role_arn
        )
