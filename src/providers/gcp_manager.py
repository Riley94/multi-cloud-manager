# src/providers/gcp_manager.py

from typing import List
from google.cloud import compute_v1
from core.models import ComputeInstance
from core.abstractions import CloudProviderInterface
import re
import warnings
from google.oauth2 import service_account
from google.auth import default
from googleapiclient import discovery
import logging

# This function should match the official documentation from Google.
def wait_for_extended_operation(operation, operation_description: str):
    # Implement or copy from the official Google samples.
    # Typically, you do something like:
    operation.result()  # Wait for the long-running operation to complete
    return f"{operation_description} completed successfully."

class GCPManager(CloudProviderInterface):
    def __init__(self, projects=None, zones=None, credentials_file=None):
        """
        projects: List of GCP projects
        zones: List of zones to query
        credentials_file: Path to GCP service account credentials JSON
        """
        self.projects = projects or []
        self.zones = zones or ["us-central1-a"]
        if credentials_file:
            # Use a service account key file
            credentials = service_account.Credentials.from_service_account_file(credentials_file)
        else:
            # Use Application Default Credentials
            credentials, _ = default(scopes=['https://www.googleapis.com/auth/cloud-platform'])

        # Build the serviceusage client with scoped_creds
        self.serviceusage = discovery.build('serviceusage', 'v1', credentials=credentials)

        # Ensure Compute Engine API is enabled for all projects
        for project in self.projects:
            self._ensure_compute_api_enabled(project)

        self.client = compute_v1.InstancesClient(credentials=credentials)

    def _ensure_compute_api_enabled(self, project_id: str):
        """
        Check if the Compute Engine API is enabled for the given project. If not, enable it.
        """
        service_name = "compute.googleapis.com"
        name = f"projects/{project_id}/services/{service_name}"

        logging.debug(f"Checking if {service_name} is enabled on project {project_id}...")

        # Get the current state of the service
        request = self.serviceusage.services().get(name=name)
        try:
            response = request.execute()
            state = response.get('state')
            if state == "ENABLED":
                logging.debug(f"{service_name} is already enabled on project {project_id}.")
            else:
                logging.debug(f"{service_name} is not enabled. Attempting to enable...")
                self.serviceusage.services().enable(name=name, body={}).execute()
                logging.info(f"Enabled {service_name} on project {project_id}.")
        except Exception as e:
            # If service does not exist or error occurs, attempt to enable regardless
            logging.warning(f"Could not get status for {service_name} on {project_id}: {e}. Trying to enable directly.")
            self.serviceusage.services().enable(name=name, body={}).execute()
            logging.info(f"Enabled {service_name} on project {project_id}.")

    def list_compute_instances(self) -> List[ComputeInstance]:
        instances = []
        for project in self.projects:
            for zone in self.zones:
                request = compute_v1.ListInstancesRequest(project=project, zone=zone)
                for inst in self.client.list(request=request):
                    # inst.machine_type is a full URL, extract the type if needed.
                    # For simplicity, we just use the URL directly.
                    instances.append(ComputeInstance(
                        instance_id=str(inst.id),
                        name=inst.name,
                        provider="gcp",
                        region=zone,
                        instance_type=inst.machine_type,
                        status=inst.status
                    ))
        return instances
    
    def create_instance(
        self,
        project: str,
        zone: str,
        instance_name: str,
        machine_type: str = "n1-standard-1",
        source_image: str = "projects/debian-cloud/global/images/family/debian-11",
        network_link: str = "global/networks/default",
        subnetwork_link: str = None,
        internal_ip: str = None,
        external_access: bool = False,
        external_ipv4: str = None,
        accelerators: list[compute_v1.AcceleratorConfig] = None,
        preemptible: bool = False,
        spot: bool = False,
        instance_termination_action: str = "STOP",
        custom_hostname: str = None,
        delete_protection: bool = False
    ) -> compute_v1.Instance:
        """
        Revised create_instance method following the official Google sample style.
        """
        logging.debug(f"Creating instance {instance_name} in project {project} zone {zone}...")
        instance_client = compute_v1.InstancesClient()

        # Configure network interface
        network_interface = compute_v1.NetworkInterface()
        network_interface.network = network_link
        if subnetwork_link:
            network_interface.subnetwork = subnetwork_link
        if internal_ip:
            network_interface.network_i_p = internal_ip
        if external_access:
            access = compute_v1.AccessConfig()
            access.type_ = compute_v1.AccessConfig.Type.ONE_TO_ONE_NAT.name
            access.name = "External NAT"
            access.network_tier = compute_v1.AccessConfig.NetworkTier.PREMIUM.name
            if external_ipv4:
                access.nat_i_p = external_ipv4
            network_interface.access_configs = [access]

        logging.debug("Network interface configured.")

        # Create a boot disk from source_image
        initialize_params = compute_v1.AttachedDiskInitializeParams(source_image=source_image)
        logging.debug("Disk params initialized.")

        disk = compute_v1.AttachedDisk()
        disk.auto_delete = True
        disk.boot = True
        disk.type_ = "PERSISTENT"
        disk.initialize_params = initialize_params
        disks = [disk]

        logging.debug("Disk configured.")

        # Prepare the Instance object
        instance = compute_v1.Instance()
        instance.network_interfaces = [network_interface]
        instance.name = instance_name
        instance.disks = disks

        logging.debug("Instance configured with disk.")

        # Validate and set machine type
        if re.match(r"^zones/[a-z\d\-]+/machineTypes/[a-z\d\-]+$", machine_type):
            instance.machine_type = machine_type
        else:
            instance.machine_type = f"zones/{zone}/machineTypes/{machine_type}"

        instance.scheduling = compute_v1.Scheduling()

        if accelerators:
            instance.guest_accelerators = accelerators
            instance.scheduling.on_host_maintenance = (
                compute_v1.Scheduling.OnHostMaintenance.TERMINATE.name
            )

        if preemptible:
            warnings.warn("Preemptible VMs are being replaced by Spot VMs.", DeprecationWarning)
            instance.scheduling.preemptible = True

        if spot:
            instance.scheduling.provisioning_model = (
                compute_v1.Scheduling.ProvisioningModel.SPOT.name
            )
            instance.scheduling.instance_termination_action = instance_termination_action

        if custom_hostname is not None:
            instance.hostname = custom_hostname

        if delete_protection:
            instance.deletion_protection = True

        request = compute_v1.InsertInstanceRequest()
        request.zone = zone
        request.project = project
        request.instance_resource = instance
        logging.debug("Request made.")
        
        operation = instance_client.insert(request=request)

        wait_for_extended_operation(operation, "instance creation")

        logging.debug("Instance created.")
        return instance_client.get(project=project, zone=zone, instance=instance_name)

    def delete_instance(self, project: str, zone: str, instance_name: str):
        instance_client = compute_v1.InstancesClient()
        print(f"Deleting instance {instance_name} from project {project} in zone {zone}...")
        operation = instance_client.delete(project=project, zone=zone, instance=instance_name)
        wait_for_extended_operation(operation, "instance deletion")
        print(f"Instance {instance_name} deleted successfully.")