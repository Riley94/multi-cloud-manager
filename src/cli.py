# src/cli.py

import argparse
import os
import yaml
from src.providers.aws_manager import AWSManager
from src.providers.gcp_manager import GCPManager

def load_config():
    # Construct path to config.yaml relative to the cli.py file
    # Assuming config.yaml is in ../config/config.yaml relative to cli.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "..", "config", "config.yaml")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at: {config_path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    return config

def main():
    config = load_config()
    parser = argparse.ArgumentParser(description="Multi-Cloud Analysis Tool")
    parser.add_argument("--aws-regions", nargs="+", help="List of AWS regions", default=["us-east-1"])
    parser.add_argument("--gcp-projects", nargs="+", help="List of GCP projects", default=[])
    parser.add_argument("--gcp-zones", nargs="+", help="List of GCP zones", default=["us-central1-a"])
    parser.add_argument("--list-instances", action="store_true", help="List compute instances from all providers")

    args = parser.parse_args()

    # Apply defaults from config
    aws_profile = config["aws"].get("profile", None)
    aws_regions = args.aws_regions if args.aws_regions else config["aws"].get("regions", ["us-east-1"])

    gcp_credentials_file = config["gcp"].get("credentials_file", None)
    gcp_projects = args.gcp_projects if args.gcp_projects else config["gcp"].get("projects", [])
    gcp_zones = args.gcp_zones if args.gcp_zones else config["gcp"].get("zones", ["us-central1-a"])

    # Instantiate managers
    aws_manager = AWSManager(regions=aws_regions)
    gcp_manager = GCPManager(projects=gcp_projects, zones=gcp_zones, credentials_file=gcp_credentials_file)

    if args.list_instances:
        aws_instances = aws_manager.list_compute_instances()
        gcp_instances = gcp_manager.list_compute_instances()

        print("=== AWS Instances ===")
        for i in aws_instances:
            print(i)

        print("=== GCP Instances ===")
        for i in gcp_instances:
            print(i)

if __name__ == "__main__":
    main()