from abc import ABC, abstractmethod
from app.domain.get import BaseGetDeviceInfo
from app.domain.models import SwitchState


class ConfigGetter(ABC):
    """
    Interface abstraite pour la récupération et le parsing de configurations.
    Implémente les principes GRASP :
    - Polymorphisme : interface commune pour tous les getters
    - Expert : chaque getter connaît comment récupérer et parser sa configuration
    """
    
    @abstractmethod
    def can_get(self, device_info: BaseGetDeviceInfo) -> bool:
        """
        Vérifie si le getter peut récupérer la configuration depuis ce type de switch.
        Implémente le principe GRASP : Expert (le getter connaît ses capacités).
        """
        ...
    
    @abstractmethod
    def get_config(self, device_info: BaseGetDeviceInfo) -> SwitchState:
        """
        Récupère et parse la configuration depuis le switch.
        Retourne un SwitchState directement utilisable par l'application.
        Implémente le principe GRASP : Creator (le getter crée le SwitchState).
        """
        ...
