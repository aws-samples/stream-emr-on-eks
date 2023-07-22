# // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# // SPDX-License-Identifier: License :: OSI Approved :: MIT No Attribution License (MIT-0)

from constructs import Construct
from aws_cdk import (Fn, RemovalPolicy, Tags, Aws, aws_iam as iam)
from lib.util.manifest_reader import load_yaml_local,load_yaml_replace_var_local
import os

class IamConst(Construct):

    @property
    def managed_node_role(self):
        return self._managed_node_role

    @property
    def admin_role(self):
        return self._clusterAdminRole
    
    @property
    def fg_pod_role(self):
        return self._fg_pod_role    

    @property
    def emr_svc_role(self):
        return self._emrsvcrole 

    @property
    def lf_engineer_role(self):
        return self._engineer_role

    @property
    def lf_analyst_role(self):
        return self._analyst_role

    @property
    def lf_sagemaker_role(self):
        return self._sm_role 

    @property
    def cloud9_ec2_role(self):
        return self._cloud9_role    

    @property
    def emr_serverless_role(self):
        return self._emrs_job_role.role_name
       

    def __init__(self,scope: Construct, id:str, cluster_name:str, code_bucket:str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        source_dir=os.path.split(os.environ['VIRTUAL_ENV'])[0]+'/source'

        # EKS admin role
        self._clusterAdminRole = iam.Role(self, 'ClusterAdmin',
            assumed_by= iam.AccountRootPrincipal()
        )
        self._clusterAdminRole.add_to_policy(iam.PolicyStatement(
            resources=["*"],
            actions=[
                "eks:Describe*",
                "eks:List*",
                "eks:AccessKubernetesApi",
                "ssm:GetParameter",
                "iam:ListRoles"
            ],
        ))
        Tags.of(self._clusterAdminRole).add(
            key='eks/%s/type' % cluster_name, 
            value='admin-role'
        )

        # Managed Node Group Instance Role
        _managed_node_managed_policies = (
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKSWorkerNodePolicy'),
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKS_CNI_Policy'),
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEC2ContainerRegistryReadOnly'),
            iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchAgentServerPolicy'), 
        )
        self._managed_node_role = iam.Role(self,'NodeInstanceRole',
            assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
            managed_policies=list(_managed_node_managed_policies),
        )
        self._managed_node_role.apply_removal_policy(RemovalPolicy.DESTROY)

        # Fargate pod execution role
        self._fg_pod_role = iam.Role(self, "FargatePodExecRole",
            assumed_by=iam.ServicePrincipal('eks-fargate-pods.amazonaws.com'),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name('AmazonEKSFargatePodExecutionRolePolicy')]
        )
        self._fg_pod_role.apply_removal_policy(RemovalPolicy.DESTROY)
        # EMR container service role
        self._emrsvcrole = iam.Role.from_role_arn(self, "EmrSvcRole", 
            role_arn=f"arn:aws:iam::{Aws.ACCOUNT_ID}:role/AWSServiceRoleForAmazonEMRContainers", 
            mutable=False
        )

        # Cloud9 EC2 role
        self._cloud9_role=iam.Role(self,"Cloud9Admin",
            assumed_by=iam.ServicePrincipal('ec2.amazonaws.com'),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name('AWSCloudFormationReadOnlyAccess')],
            description="cloud9admin"
        )
        self._cloud9_role.add_to_policy(iam.PolicyStatement(
            resources=[self._clusterAdminRole.role_arn],
            actions=["sts:AssumeRole"]
        ))
        _c9_iam = load_yaml_replace_var_local(source_dir+'/app_resources/cloud9-iam-role.yaml', 
            fields= {
                "{{REGION}}": Aws.REGION,
                "{{AccountID}}": Aws.ACCOUNT_ID
            })
        for statmnt in _c9_iam:
            self._cloud9_role.add_to_policy(iam.PolicyStatement.from_json(statmnt)
        )
        iam.CfnInstanceProfile(self,"Cloud9RoleProfile",
            roles=[ self._cloud9_role.role_name],
            instance_profile_name= self._cloud9_role.role_name
        )
        self._cloud9_role.apply_removal_policy(RemovalPolicy.DESTROY)

        # lf data access engineer role
        self._engineer_role=iam.Role(self,"LFEngineer",
            role_name="lf-data-access-engineer",
            assumed_by=iam.CompositePrincipal(
                    iam.ServicePrincipal("lakeformation.amazonaws.com")
            ),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess')]
        )
        _engineer_iam = load_yaml_replace_var_local(source_dir+'/app_resources/lf-engineer-iam-role.yaml', 
            fields= {
                "{{REGION}}": Aws.REGION,
                "{{AccountID}}": Aws.ACCOUNT_ID
            })
        for statmnt in _engineer_iam:
            self._engineer_role.add_to_policy(iam.PolicyStatement.from_json(statmnt)
        )
        self._engineer_role.apply_removal_policy(RemovalPolicy.DESTROY)

        # lf data access analyst role
        self._analyst_role=iam.Role(self,"LFAnalyst",
            role_name="lf-data-access-analyst",
            assumed_by=iam.ServicePrincipal('lakeformation.amazonaws.com'),
            managed_policies=[iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess')]
        )
        _analyst_iam = load_yaml_local(source_dir+'/app_resources/lf-analyst-iam-role.yaml')
        for statmnt in _analyst_iam:
            self._analyst_role.add_to_policy(iam.PolicyStatement.from_json(statmnt)
        )
        self._analyst_role.apply_removal_policy(RemovalPolicy.DESTROY)

        # lf sagemaker role
        self._sm_role=iam.Role(self,"sagemaker",
            role_name="lf-sagemaker-role",  
            assumed_by=iam.ServicePrincipal('sagemaker.amazonaws.com')
        )
        _sm_iam = load_yaml_replace_var_local(source_dir+'/app_resources/lf-sagemaker-role.yaml', 
            fields= {
                "{{AccountID}}": Aws.ACCOUNT_ID,
                "{{codeBucket}}": code_bucket
            })
        for statmnt in _sm_iam:
            self._sm_role.add_to_policy(iam.PolicyStatement.from_json(statmnt)
        )
        self._sm_role.apply_removal_policy(RemovalPolicy.DESTROY)

        # EMR Serverless job runtime role
        self._emrs_job_role = iam.Role(self,'EMRServerlessRuntimeRole',
            assumed_by=iam.ServicePrincipal('emr-serverless.amazonaws.com')
        )
        _emrs_iam = load_yaml_replace_var_local(source_dir+'/app_resources/emr-serverless-iam-role.yaml', 
            fields= {
                "{{codeBucket}}": code_bucket,
                "{{AccountID}}": Aws.ACCOUNT_ID
            })
        for statmnt in _emrs_iam:
            self._emrs_job_role.add_to_policy(iam.PolicyStatement.from_json(statmnt)
        )
        self._emrs_job_role.apply_removal_policy(RemovalPolicy.DESTROY)
