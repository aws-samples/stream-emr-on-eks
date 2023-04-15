# // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# // SPDX-License-Identifier: License :: OSI Approved :: MIT No Attribution License (MIT-0)
#
from constructs import Construct
from aws_cdk import (DefaultStackSynthesizer,Fn,Aws,NestedStack,RemovalPolicy,aws_s3 as s3,aws_iam as iam,aws_lakeformation as lf)


class LFStack(NestedStack):

    def __init__(self, scope: Construct, id: str, engineer_role: iam.IRole, analyst_role: iam.IRole, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create an empty datalake S3 bucket
        self.lf_bucket=s3.Bucket(self, "LFbucket", 
            bucket_name=f"lf-datalake-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS_MANAGED,
            removal_policy= RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Register the s3 as data lake location
        _dl_location=lf.CfnResource(self, "DataLakeLoation",
            resource_arn=self.lf_bucket.bucket_arn,
            use_service_linked_role=False,
            role_arn=engineer_role.role_arn
        )
  
        # The role assumed by cdk is not a data lake administrator.
        # So, deploying PrincipalPermissions meets the error such as:
        # "Resource does not exist or requester is not authorized to access requested permissions."
        # In order to solve the error, it is necessary to promote the cdk execution role to the data lake administrator.
        default_cdk_exec_role=f"arn:aws:iam::{Aws.ACCOUNT_ID}:role/cdk-hnb659fds-cfn-exec-role-{Aws.ACCOUNT_ID}-{Aws.REGION}"
        cfn_data_lake_settings = lf.CfnDataLakeSettings(self, "CfnDataLakeSettings",
            admins=[lf.CfnDataLakeSettings.DataLakePrincipalProperty(
                data_lake_principal_identifier=default_cdk_exec_role
            )]
        )
        cfn_data_lake_settings.apply_removal_policy(RemovalPolicy.DESTROY)
        
        # Create a Data location for engineer role
        engineer_perm = lf.CfnPrincipalPermissions(self, "EngineerDataLocation",
            permissions=["DATA_LOCATION_ACCESS"],
            permissions_with_grant_option=[],
            principal=lf.CfnPrincipalPermissions.DataLakePrincipalProperty(
                data_lake_principal_identifier=engineer_role.role_arn
            ),
            resource=lf.CfnPrincipalPermissions.ResourceProperty(
                data_location=lf.CfnPrincipalPermissions.DataLocationResourceProperty(
                    catalog_id=Aws.ACCOUNT_ID,
                    resource_arn=self.lf_bucket.bucket_arn
                )
            )    
        )
        engineer_perm.add_dependency(cfn_data_lake_settings)
        engineer_perm.apply_removal_policy(RemovalPolicy.DESTROY)  

        # Add a Database permission for analyst role
        analyst_perm = lf.CfnPrincipalPermissions(self, "analystDBPermission",
            permissions=["DESCRIBE"],
            permissions_with_grant_option=[],
            principal=lf.CfnPrincipalPermissions.DataLakePrincipalProperty(
                data_lake_principal_identifier=analyst_role.role_arn
            ),
            resource=lf.CfnPrincipalPermissions.ResourceProperty(
                database=lf.CfnPrincipalPermissions.DatabaseResourceProperty(
                    catalog_id=Aws.ACCOUNT_ID,
                    name="default"
                )
            )
        )
        analyst_perm.add_dependency(cfn_data_lake_settings)
        analyst_perm.apply_removal_policy(RemovalPolicy.DESTROY)