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
    
    def get_amis(self, region: str) -> List[dict]:
        """
        Retrieve a list of AMIs available in the specified region. 
        For this example, we'll filter for Amazon Linux 2 AMIs owned by Amazon.
        Returns a list of dicts with 'ImageId' and 'Name'.
        """
        ec2 = self.session.client('ec2', region_name=region)
        # Filter for Amazon Linux 2 AMIs (HVM, EBS-backed, x86_64)
        # Pattern often: "amzn2-ami-hvm-2.0.*-x86_64-gp2"
        response = ec2.describe_images(
            Owners=['amazon'],
            Filters=[
                {'Name': 'name', 'Values': ['amzn2-ami-hvm-2.0.*-x86_64-gp2']}
            ]
        )
        # Sort images by CreationDate descending, so the newest AMI is first.
        images = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)
        # Return a simplified list
        ami_list = [{'ImageId': img['ImageId'], 'Name': img.get('Name', img['ImageId'])} for img in images]
        return ami_list
    
    def create_instance(self, name: str, region: str, instance_type: str, image_id: str, key_name: str = None, security_group_ids: List[str] = None, subnet_id: str = None, count: int = 1):
        """
        Create a new AWS EC2 instance.
        :param name: The Name tag for the instance
        :param region: The AWS region to create the instance in.
        :param instance_type: The instance type (e.g., 't2.micro').
        :param image_id: The AMI ID to launch (e.g., 'ami-0abcdef1234567890').
        :param key_name: Optional key pair name to associate with the instance.
        :param security_group_ids: List of security group IDs to associate.
        :param subnet_id: Optional subnet ID to launch into a specific subnet of a VPC.
        :param count: Number of instances to create.
        """
        ec2 = self.session.client('ec2', region_name=region)
        params = {
            'ImageId': image_id,
            'InstanceType': instance_type,
            'MinCount': count,
            'MaxCount': count,
        }

        if key_name:
            params['KeyName'] = key_name
        if security_group_ids:
            params['SecurityGroupIds'] = security_group_ids
        if subnet_id:
            params['SubnetId'] = subnet_id

        response = ec2.run_instances(**params)

        instance_ids = [i['InstanceId'] for i in response['Instances']]

        # Add a Name tag if provided
        if name:
            ec2.create_tags(
                Resources=instance_ids,
                Tags=[{'Key': 'Name', 'Value': name}]
            )

        return instance_ids  # Return the created instance IDs

    def delete_instance(self, instance_id: str, region: str):
        """
        Delete (terminate) an AWS EC2 instance.
        :param instance_id: The ID of the instance to terminate.
        :param region: The region of the instance.
        """
        ec2 = self.session.client('ec2', region_name=region)
        print(f"Terminating instance {instance_id} in region {region}...")
        ec2.terminate_instances(InstanceIds=[instance_id])
        print(f"Instance {instance_id} termination initiated.")

    def get_instance_details(self, instance_id: str, region: str):
        """
        Retrieve details of a specific instance by ID.
        Returns a dictionary of instance data, including tags.
        """
        ec2 = self.session.client('ec2', region_name=region)
        response = ec2.describe_instances(InstanceIds=[instance_id])
        reservations = response.get("Reservations", [])
        if reservations and "Instances" in reservations[0]:
            return reservations[0]["Instances"][0]
        return None

    def modify_instance(self, instance_id: str, region: str, tags: List[dict]):
        """
        Modify an instance by updating its tags.
        :param instance_id: The instance to modify.
        :param region: The region of the instance.
        :param tags: A list of tag dictionaries: [{'Key': 'key', 'Value': 'value'}, ...]
        """
        ec2 = self.session.client('ec2', region_name=region)
        # If tags is empty, consider what to do. Currently, we just update whatever keys are given.
        # This replaces or adds tags. Existing tags not mentioned won't be deleted automatically; to remove tags, call ec2.delete_tags().
        if tags:
            ec2.create_tags(
                Resources=[instance_id],
                Tags=tags
            )
            print(f"Instance {instance_id} tags updated successfully.")
        else:
            print("No tags provided. No changes made.")