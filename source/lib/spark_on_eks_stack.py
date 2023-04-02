# // Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# // SPDX-License-Identifier: License :: OSI Approved :: MIT No Attribution License (MIT-0)

from aws_cdk import (Stack,CfnParameter,Fn)
from constructs import Construct
from lib.cdk_infra.network_sg import NetworkSgConst
from lib.cdk_infra.iam_roles import IamConst
from lib.cdk_infra.eks_cluster import EksConst
from lib.cdk_infra.eks_service_account import EksSAConst
from lib.cdk_infra.eks_base_app import EksBaseAppConst
from lib.cdk_infra.s3_app_code import S3AppCodeConst
from lib.cdk_infra.spark_permission import SparkOnEksConst
from lib.util.manifest_reader import *

class SparkOnEksStack(Stack):

    @property
    def code_bucket(self):
        return self.app_s3.code_bucket

    @property
    def eksvpc(self):
        return self.network_sg.vpc

    @property
    def EMRVC(self):
        return self.emr.EMRVC

    @property
    def EMRExecRole(self):
        return self.emr.EMRExecRole    

    @property
    def LFEngineerRole(self):
        return self.iam.lf_engineer_role  

    @property
    def LFAnalystRole(self):
        return self.iam.lf_analyst_role  

    @property
    def LFSagemakerRole(self):
        return self.iam.lf_sagemaker_role   

    @property
    def assetURL(self):
        return self.assets_url_param    

    @property
    def assetS3(self):
        return self.assets_s3_bucket

    def __init__(self, scope: Construct, id: str, eksname: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # 1. a new bucket to store application code
        self.app_s3 = S3AppCodeConst(self,'appcode')

        self.assets_url_param = CfnParameter(self,'WorkshopAssetsURL', 
            description='workshop studio assets bucket and prefix',
            default='s3://mybucket'
        ).value_as_string
        self.assets_s3_bucket=Fn.select(2,Fn.split('/',self.assets_url_param))
 
        # 2. EKS base infra
        self.network_sg = NetworkSgConst(self,'network-sg', eksname)
        self.iam = IamConst(self,'iam_roles', eksname, self.assets_url_param, self.assets_s3_bucket)
        self.eks_cluster = EksConst(self,'eks_cluster', eksname, self.network_sg.vpc, self.iam.managed_node_role, self.iam.admin_role, self.iam.emr_svc_role, self.iam.fg_pod_role, self.iam.cloud9_ec2_role)
        EksSAConst(self, 'eks_service_account', self.eks_cluster.my_cluster)
        EksBaseAppConst(self, 'eks_base_app', self.eks_cluster.my_cluster)

        # 3. Setup Spark environment, Register for EMR on EKS
        self.emr = SparkOnEksConst(self,'spark_permission',self.eks_cluster.my_cluster, self.app_s3.code_bucket)