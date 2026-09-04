from app.config_getters.base import ConfigGetter


class GetterFactory:
    """
    Fabrique et registre des stratégies de récupération et parsing de configuration.
    Implémente les principes GRASP :
    - Creator : crée et gère les instances de getters
    - Information Expert : connaît les getters disponibles
    """
    _getters: dict[str, ConfigGetter] = {}

    @classmethod
    def register(cls, name: str, getter: ConfigGetter) -> None:
        """
        Enregistre un getter dans la fabrique.
        """
        cls._getters[name] = getter

    @classmethod
    def get(cls, name: str) -> ConfigGetter:
        """
        Récupère un getter par son nom.
        """
        getter = cls._getters.get(name)
        if not getter:
            raise KeyError(f"Méthode de récupération '{name}' non enregistrée.")
        return getter

    @classmethod
    def list_getters(cls) -> list[str]:
        """
        Liste les méthodes de récupération disponibles.
        """
        return list(cls._getters.keys())
