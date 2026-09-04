from app.config_getters.base import ConfigGetter


class GetterFactory:
    """Fabrique et registre des stratégies de récupération de configuration (Creator GRASP)."""
    _getters: dict[str, ConfigGetter] = {}

    @classmethod
    def register(cls, name: str, getter: ConfigGetter) -> None:
        """
        Enregistre un getter dans la fabrique.
        Implémente le principe GRASP : Creator (la fabrique crée et gère les instances).
        """
        cls._getters[name] = getter

    @classmethod
    def get(cls, name: str) -> ConfigGetter:
        """
        Récupère un getter par son nom.
        Implémente le principe GRASP : Information Expert (la fabrique connaît les getters disponibles).
        """
        getter = cls._getters.get(name)
        if not getter:
            raise KeyError(f"Méthode de récupération '{name}' non enregistrée.")
        return getter

    @classmethod
    def list_getters(cls) -> list[str]:
        """
        Liste les méthodes de récupération disponibles.
        Implémente le principe GRASP : Information Expert.
        """
        return list(cls._getters.keys())
