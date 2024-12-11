# tests/test_aws_manager.py

import unittest
from unittest.mock import patch, MagicMock
from src.providers.aws_manager import AWSManager

class TestAWSManager(unittest.TestCase):

    @patch("boto3.Session")
    def test_list_compute_instances(self, mock_session):
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_client.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": "i-1234567890abcdef0",
                            "InstanceType": "t2.micro",
                            "State": {"Name": "running"},
                            "Tags": [{"Key": "Name", "Value": "TestInstance"}]
                        }
                    ]
                }
            ]
        }

        manager = AWSManager(regions=["us-east-1"])
        instances = manager.list_compute_instances()
        self.assertEqual(len(instances), 1)
        self.assertEqual(instances[0].instance_id, "i-1234567890abcdef0")
        self.assertEqual(instances[0].name, "TestInstance")
        self.assertEqual(instances[0].status, "running")

if __name__ == '__main__':
    unittest.main()