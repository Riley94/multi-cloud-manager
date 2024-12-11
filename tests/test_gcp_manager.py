# tests/test_gcp_manager.py

import unittest
from unittest.mock import patch, MagicMock
from src.providers.gcp_manager import GCPManager
from google.cloud.compute_v1.types import Instance

class TestGCPManager(unittest.TestCase):

    @patch("google.cloud.compute_v1.InstancesClient")
    def test_list_compute_instances(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_instance = Instance(
            id=123456789,
            name="gcp-test-instance",
            machine_type="https://www.googleapis.com/compute/v1/projects/my-proj/zones/us-central1-a/machineTypes/n1-standard-1",
            status="RUNNING"
        )

        mock_client.list.return_value = [mock_instance]

        manager = GCPManager(projects=["my-proj"], zones=["us-central1-a"])
        instances = manager.list_compute_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].instance_id, "123456789")
        self.assertEqual(instances[0].name, "gcp-test-instance")
        self.assertEqual(instances[0].status, "RUNNING")

if __name__ == '__main__':
    unittest.main()