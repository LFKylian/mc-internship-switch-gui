from app.config_pushers.base import ConfigPusher


class PusherFactory:
    """Fabrique et registre des stratégies de déploiement."""
    _pushers: dict[str, ConfigPusher] = {}

    @classmethod
    def register(cls, name: str, pusher: ConfigPusher) -> None:
        cls._pushers[name] = pusher

    @classmethod
    def get(cls, name: str) -> ConfigPusher:
        pusher = cls._pushers.get(name)
        if not pusher:
            raise KeyError(f"Méthode de déploiement '{name}' non enregistrée.")
        return pusher