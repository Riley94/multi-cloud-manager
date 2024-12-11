# src/providers/aws_manager.py

import boto3
from typing import List
from core.models import ComputeInstance
from core.abstractions import CloudProviderInterface

class AWSManager(CloudProviderInterface):
    def __init__(self, regions=None, profile=None):
        """
        regions: List of AWS regions to query
        profile: Optional AWS CLI profile name to use
        """
        self.regions = regions or ["us-east-1"]
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()

    def list_compute_instances(self) -> List[ComputeInstance]:
        instances = []
        for region in self.regions:
            ec2 = self.session.client('ec2', region_name=region)
            response = ec2.describe_instances()
            for reservation in response["Reservations"]:
                for inst in reservation["Instances"]:
                    name = None
                    if 'Tags' in inst:
                        for tag in inst['Tags']:
                            if tag['Key'] == 'Name':
                                name = tag['Value']
                                break

                    instances.append(ComputeInstance(
                        instance_id=inst["InstanceId"],
                        name=name,
                        provider="aws",
                        region=region,
                        instance_type=inst["InstanceType"],
                        status=inst["State"]["Name"]
                    ))
        return instances