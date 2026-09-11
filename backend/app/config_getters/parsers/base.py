from abc import ABC, abstractmethod
from app.domain.models import SwitchState


class ConfigParser(ABC):
    """
    Interface abstraite pour le parsing de configurations brutes en SwitchState.
    Implémente les principes GRASP :
    - Polymorphisme : interface commune pour tous les parseurs
    - Expert : chaque parseur connaît le format de configuration de son OS
    """
    
    @abstractmethod
    def can_parse(self, raw_config: str) -> bool:
        """
        Vérifie si ce parseur peut parser cette configuration.
        """
        ...
    
    @abstractmethod
    def parse(self, raw_config: str) -> SwitchState:
        """
        Parse la configuration brute et retourne un SwitchState.
        """
        ...
