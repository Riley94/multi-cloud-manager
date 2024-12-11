# src/app.py

import os
import yaml
from flask import Flask, render_template, request, redirect, url_for, flash
from providers.aws_manager import AWSManager
from providers.gcp_manager import GCPManager
import secrets
import logging
logging.basicConfig(level=logging.DEBUG)

def load_config():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "..", "config", "config.yaml")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at: {config_path}")

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

@app.route("/")
def index():
    # This page will display provider options
    return render_template("index.html")

@app.route("/aws")
def aws_page():
    # Load config if needed, or default profiles from config.yaml
    config = load_config()
    aws_profile = config["aws"].get("profile", None)
    aws_regions = config["aws"].get("regions", ["us-east-1"])

    aws_manager = AWSManager(regions=aws_regions, profile=aws_profile)
    aws_instances = aws_manager.list_compute_instances()

    return render_template("aws.html", instances=aws_instances)

@app.route("/aws/create", methods=["GET", "POST"])
def create_aws_instance():
    # On POST, call aws_manager.create_instance(...) and then flash a message/redirect.
    config = load_config()
    aws_profile = config["aws"].get("profile", None)
    aws_regions = config["aws"].get("regions", ["us-east-1"])
    # Default to the first region for AMI retrieval or let user pick a region first (for simplicity we pick first)
    default_region = aws_regions[0]
    aws_manager = AWSManager(regions=[default_region], profile=aws_profile)
    # GET request: Retrieve AMIs for the default region
    amis = aws_manager.get_amis(default_region)

    if request.method == "POST":
        # Extract form data for instance creation
        instance_name = request.form.get("instance_name")
        region = request.form.get("region") or "us-east-1"
        instance_type = request.form.get("instance_type") or "t2.micro"
        image_id = request.form.get("image_id") or "ami-1234567890abcdef0"

        try:
            aws_manager.create_instance(
                name=instance_name,
                region=region,
                instance_type=instance_type,
                image_id=image_id
            )
            flash(f"Instance {instance_name} created successfully.")
        except Exception as e:
            flash(f"Error creating instance: {e}")
        return redirect(url_for('aws_page'))

    return render_template("create_aws_instance.html", regions=aws_regions, amis=amis)

@app.route("/aws/delete/<instance_id>")
def delete_aws_instance(instance_id):
    config = load_config()
    aws_profile = config["aws"].get("profile", None)
    aws_regions = config["aws"].get("regions", ["us-east-1"])
    region = request.args.get("region")
    if not region:
        flash("No region specified for instance deletion.")
        return redirect(url_for('aws_page'))

    aws_manager = AWSManager(regions=[region], profile=aws_profile)
    try:
        aws_manager.delete_instance(instance_id=instance_id, region=region)
        flash(f"Instance {instance_id} deleted successfully.")
    except Exception as e:
        flash(f"Error deleting instance {instance_id}: {e}")
    return redirect(url_for('aws_page'))

@app.route("/aws/modify/<instance_id>", methods=["GET", "POST"])
def modify_aws_instance(instance_id):
    config = load_config()
    aws_profile = config["aws"].get("profile", None)
    region = request.args.get("region")
    if not region:
        flash("No region specified for instance modification.")
        return redirect(url_for('aws_page'))

    aws_manager = AWSManager(regions=[region], profile=aws_profile)

    if request.method == "POST":
        # Parse form data to modify instance
        tag_keys = request.form.getlist("tag_key")
        tag_vals = request.form.getlist("tag_value")
        tags = []
        for k, v in zip(tag_keys, tag_vals):
            if k.strip():
                tags.append({'Key': k.strip(), 'Value': v.strip()})

        try:
            aws_manager.modify_instance(instance_id=instance_id, region=region, tags=tags)
            flash(f"Instance {instance_id} updated successfully.")
        except Exception as e:
            flash(f"Error modifying instance {instance_id}: {e}")

        return redirect(url_for('aws_page'))

    # GET request: show the current tags or properties
    instance_details = aws_manager.get_instance_details(instance_id=instance_id, region=region)
    current_tags = instance_details.get('Tags', [])  # depends on aws_manager implementation

    return render_template("modify_aws_instance.html", instance_id=instance_id, region=region, tags=current_tags)

@app.route("/gcp")
def gcp_page():
    # Load config
    config = load_config()
    
    gcp_credentials_file = config["gcp"].get("credentials_file", None)
    gcp_projects = config["gcp"].get("projects", [])
    gcp_zones = config["gcp"].get("zones", ["us-central1-a"])

    gcp_manager = GCPManager(projects=gcp_projects, zones=gcp_zones, credentials_file=gcp_credentials_file)
    gcp_instances = gcp_manager.list_compute_instances()

    # Render GCP page with instance info
    return render_template("gcp.html", instances=gcp_instances)

@app.route("/gcp/create", methods=["GET", "POST"])
def create_gcp_instance():
    config = load_config()
    gcp_credentials_file = config["gcp"].get("credentials_file", None)
    gcp_projects = config["gcp"].get("projects", [])
    # Assume we use the first project listed in config
    project = gcp_projects[0] if gcp_projects else None

    if request.method == "POST":
        # Get form data
        project = request.form.get("project") or project
        instance_name = request.form.get("instance_name")  # should be a non-empty string
        zone = request.form.get("zone") or "us-central1-a"
        machine_type = request.form.get("machine_type") or "n1-standard-1"
        source_image = request.form.get("source_image") or "projects/debian-cloud/global/images/family/debian-11"
        network = "global/networks/default"

        if not project:
            flash("No GCP project configured. Unable to create an instance.")
            return redirect(url_for('gcp_page'))

        gcp_manager = GCPManager(projects=[project], zones=[zone], credentials_file=gcp_credentials_file)
        
        try:
            logging.debug(f"About to create instance with: project={project}, zone={zone}, instance_name={instance_name}, "
              f"machine_type={machine_type}, source_image={source_image}, network={network}")
            instance = gcp_manager.create_instance(
                project=project,
                zone=zone,
                instance_name=instance_name,
                machine_type=machine_type,
                source_image=source_image,
                network_link=network
            )
            flash(f"Instance created: {instance.name}")
            return redirect(url_for('gcp_page'))
        except Exception as e:
            flash(f"Error creating instance: {e}")
            return redirect(url_for('gcp_page'))

    # GET request shows the form
    return render_template("create_gcp_instance.html", gcp_projects=gcp_projects)

@app.route("/gcp/delete/<instance_name>")
def delete_gcp_instance(instance_name):
    config = load_config()
    gcp_projects = config["gcp"].get("projects", [])
    gcp_credentials_file = config["gcp"].get("credentials_file", None)

    # Get the zone and project from query parameter
    zone = request.args.get("zone")
    project = request.args.get("project")
    if not project or not zone:
        flash("No zone or project specified for instance deletion.")
        return redirect(url_for('gcp_page'))

    gcp_manager = GCPManager(projects=[project], zones=[zone], credentials_file=gcp_credentials_file)
    try:
        gcp_manager.delete_instance(project=project, zone=zone, instance_name=instance_name)
        flash(f"Instance {instance_name} deleted successfully.")
    except Exception as e:
        flash(f"Error deleting instance {instance_name}: {e}")
    return redirect(url_for('gcp_page'))

@app.route("/gcp/modify/<instance_name>", methods=["GET", "POST"])
def modify_gcp_instance(instance_name):
    project = request.args.get("project")
    zone = request.args.get("zone")
    if not project or not zone:
        flash("Missing project or zone for modifying instance.")
        return redirect(url_for('gcp_page'))

    config = load_config()
    gcp_credentials_file = config["gcp"].get("credentials_file", None)
    gcp_manager = GCPManager(projects=[project], zones=[zone], credentials_file=gcp_credentials_file)

    if request.method == "POST":
        # Parse form data for labels and metadata
        # Labels and metadata likely come in as key-value pairs
        label_keys = request.form.getlist("label_key")
        label_vals = request.form.getlist("label_value")
        metadata_keys = request.form.getlist("metadata_key")
        metadata_vals = request.form.getlist("metadata_value")

        labels = {}
        for k, v in zip(label_keys, label_vals):
            if k.strip():
                labels[k.strip()] = v.strip()

        metadata = {}
        for k, v in zip(metadata_keys, metadata_vals):
            if k.strip():
                metadata[k.strip()] = v.strip()

        try:
            gcp_manager.set_instance_labels(project, zone, instance_name, labels)
            gcp_manager.set_instance_metadata(project, zone, instance_name, metadata)
            flash(f"Instance {instance_name} updated successfully.")
        except Exception as e:
            flash(f"Error modifying instance: {e}")

        return redirect(url_for('gcp_page'))

    # GET request: Show current labels and metadata
    instance = gcp_manager.get_instance_details(project, zone, instance_name)
    current_labels = instance.labels or {}
    current_metadata = {}
    if instance.metadata and instance.metadata.items:
        for item in instance.metadata.items:
            current_metadata[item.key] = item.value

    return render_template("modify_gcp_instance.html",
                           instance_name=instance_name,
                           project=project,
                           zone=zone,
                           labels=current_labels,
                           metadata=current_metadata)

if __name__ == "__main__":
    # Run the Flask app
    # In production, use a WSGI server or other deployment strategies.
    app.run(debug=True)