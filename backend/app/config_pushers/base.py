from abc import ABC, abstractmethod
from app.domain.push import BaseDeviceInfo

class ConfigPusher(ABC):
    @abstractmethod
    def push_config(self, pushing_device_info: BaseDeviceInfo, commands: list[str]) -> str:
        """Interface commune pour l'envoi de configurations (Polymorphisme GRASP)."""
        ...