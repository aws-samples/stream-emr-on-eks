# // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# // SPDX-License-Identifier: License :: OSI Approved :: MIT No Attribution License (MIT-0)
#
from constructs import Construct
from aws_cdk import (Fn,Aws,NestedStack,RemovalPolicy,aws_s3 as s3,aws_iam as iam,aws_lakeformation as lf)
import boto3

class LFStack(NestedStack):

    def __init__(self, scope: Construct, id: str, engineer_role: iam.IRole,lf_bucket:s3.IBucket, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Register the s3 as data lake location
        _dl_location=lf.CfnResource(self, "DataLakeLoation",
            resource_arn=lf_bucket.bucket_arn,
            use_service_linked_role=False,
            role_arn=engineer_role.role_arn
        )
  
        # The role assumed by cdk is not a data lake administrator.
        # So, deploying PrincipalPermissions meets the error such as:
        # "Resource does not exist or requester is not authorized to access requested permissions."
        # In order to solve the error, it is necessary to promote the cdk execution role to the data lake administrator.
        iam_client = boto3.client("iam")
        sts_client = boto3.client("sts").get_caller_identity()
        # account_id = sts_client.get("Account")
        # region_name = boto3.client('s3').meta.region_name
        # default_cdk_exec_role=f'cdk-hnb659fds-cfn-exec-role-{account_id}-{region_name}'
        try:
            iam_client.get_role(RoleName='WSParticipantRole')
            _dladmin = lf.CfnDataLakeSettings(self, "CfnDataLakeAdmin",
                admins=[lf.CfnDataLakeSettings.DataLakePrincipalProperty(
                    data_lake_principal_identifier=f"arn:aws:iam::{Aws.ACCOUNT_ID}:role/cdk-hnb659fds-cfn-exec-role-{Aws.ACCOUNT_ID}-{Aws.REGION}"
                )]
            )
        except iam_client.exceptions.NoSuchEntityException:
            _current_arn = sts_client.get("Arn")
            _dladmin = lf.CfnDataLakeSettings(self, "CfnDataLakeAdmin2",
                admins=[lf.CfnDataLakeSettings.DataLakePrincipalProperty(
                    data_lake_principal_identifier=_current_arn
                )]
            )
        finally:
            _dladmin.apply_removal_policy(RemovalPolicy.DESTROY)
        
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
                    resource_arn=lf_bucket.bucket_arn
                )
            )    
        )
        engineer_perm.add_dependency(_dladmin)
        engineer_perm.add_dependency(_dl_location)
        engineer_perm.apply_removal_policy(RemovalPolicy.DESTROY)