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

if __name__ == "__main__":
    # Run the Flask app
    # In production, use a WSGI server or other deployment strategies.
    app.run(debug=True)