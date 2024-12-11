# src/core/abstractions.py
from abc import ABC, abstractmethod
from typing import List
from .models import ComputeInstance

class CloudProviderInterface(ABC):
    @abstractmethod
    def list_compute_instances(self) -> List[ComputeInstance]:
        """List all compute instances for this provider."""
        pass