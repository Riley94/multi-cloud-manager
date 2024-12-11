# src/core/models.py

class ComputeInstance:
    def __init__(self, instance_id, name, provider, region, instance_type, status):
        self.instance_id = instance_id
        self.name = name
        self.provider = provider
        self.region = region
        self.instance_type = instance_type
        self.status = status

    def __repr__(self):
        return (f"<ComputeInstance provider={self.provider} id={self.instance_id} "
                f"name={self.name} region={self.region} type={self.instance_type} status={self.status}>")