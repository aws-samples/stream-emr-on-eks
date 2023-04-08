# // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# // SPDX-License-Identifier: License :: OSI Approved :: MIT No Attribution License (MIT-0)
#
from constructs import Construct
from aws_cdk import (Fn,Aws,NestedStack,RemovalPolicy,aws_s3 as s3,aws_iam as iam,aws_lakeformation as lf)


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
        # Create a Data location for engineer role
        _engineer_role=lf.CfnPermissions.DataLakePrincipalProperty(
            data_lake_principal_identifier=engineer_role.role_arn
        )
        data_location1=lf.CfnPermissions(self, "DataLocation", 
            data_lake_principal=_engineer_role,
            resource=lf.CfnPermissions.ResourceProperty(
                data_location_resource=lf.CfnPermissions.DataLocationResourceProperty(
                    s3_resource=self.lf_bucket.bucket_arn
                )
            ),
            permissions=['DATA_LOCATION_ACCESS']
        )
        data_location1.add_dependency(_dl_location)
        
        # create a describe permission for analyst role to access default DB
        _analyst_principal=lf.CfnPermissions.DataLakePrincipalProperty(
                data_lake_principal_identifier=analyst_role.role_arn
        )
        _data_location2=lf.CfnPermissions(self, "DBDataLocation", 
            data_lake_principal=_analyst_principal
            resource=lf.CfnPermissions.ResourceProperty(
                database_resource=lf.CfnPermissions.DatabaseResourceProperty(name="default")
            ),
            permissions=['DESCRIBE']
        )
        _data_location2.add_dependency(_data_location1)