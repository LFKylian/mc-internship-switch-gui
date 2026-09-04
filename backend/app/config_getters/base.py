from abc import ABC, abstractmethod
from app.domain.get import BaseGetDeviceInfo


class ConfigGetter(ABC):
    """Interface abstraite pour la récupération de configurations (Polymorphisme GRASP)."""
    
    @abstractmethod
    def can_get(self, device_info: BaseGetDeviceInfo) -> bool:
        """
        Vérifie si le getter peut récupérer la configuration depuis le switch.
        Implémente le principe GRASP : Expert (le getter connaît ses propres capacités).
        """
        ...
    
    @abstractmethod
    def get_config(self, device_info: BaseGetDeviceInfo) -> str:
        """
        Récupère la configuration depuis le switch.
        Implémente le principe GRASP : Creator (le getter crée la configuration à partir du switch).
        """
        ...
