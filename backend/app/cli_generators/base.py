from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.models import SwitchState
from app.switch_profiles.base import SwitchProfile


class ConfigOutputGenerator(ABC):
    """
    Contrat GRASP Polymorphism : toute sortie de configuration (CLI, futur
    playbook Ansible...) implémente cette interface. Le reste de l'application
    ne dépend jamais d'une implémentation concrète, seulement de ce contrat —
    c'est ce qui permettra d'ajouter AnsiblePlaybookGenerator plus tard sans
    toucher au contrôleur ni au moteur de domaine.
    """

    @abstractmethod
    def generate(self, profile: SwitchProfile, state: SwitchState) -> str: ...
