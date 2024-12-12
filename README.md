# multi-cloud-manager

Multi-Cloud Instance Manager
This project provides a web application for managing virtual machine instances and storage buckets across Google Cloud Platform (GCP) and Amazon Web Services (AWS).

## Features:

Multi-Cloud Support: Manage instances on both GCP and AWS from a single interface. \
Instance Management: Create, delete, and modify virtual machine instances. \
Bucket Management (AWS): Create and delete S3 buckets on AWS. \
Configuration Management: Define projects and regions through config.yaml. \
Flask Framework: Leverages Flask for a lightweight and flexible web application.

## Installation
Create a virtual environment. \
Linux/macOS: python3 -m venv venv \
Windows: Refer to official documentation for creating a virtual environment. \
Activate the virtual environment. \
Install dependencies: pip install -r requirements.txt \

## Usage
Include config/config.yaml with your project IDs, regions, and other configurations. \
Run the application: python app.py \
Access the application in your web browser at http://localhost:5000 (default port). \
Note: Authentication is currently handled through default system configurations. For production use, consider implementing  more robust authentication mechanisms.

Run the application with python -m src.app
