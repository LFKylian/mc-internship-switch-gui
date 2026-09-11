from enum import Enum
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field, SecretStr


class GetMethods(Enum):
    """Les différentes méthodes de récupération de configuration supportées."""
    SSH = "ssh"


class BaseGetDeviceInfo(BaseModel):
    """Informations de base pour toutes les méthodes de récupération."""
    method: str
    host: str
    username: str
    password: SecretStr


class SSHGetDeviceInfo(BaseGetDeviceInfo):
    """Informations de connexion SSH spécifiques (similaires à SSHDeviceInfo pour push)."""
    method: Literal["ssh"] = "ssh"  # champs discriminant
    device_type: str
    port: int = 22
    secret: SecretStr = SecretStr("")
    show_running_config_cmd: str = "show running-config"

    def to_netmiko_dict(self) -> dict:
        """Convertit le modèle en dictionnaire compatible Netmiko en déballant les SecretStr."""
        data = self.model_dump()
        data.pop("method", None)
        data.pop("show_running_config_cmd", None)
        data["password"] = self.password.get_secret_value()
        data["secret"] = self.secret.get_secret_value()
        return data


# Union discriminée : Pydantic identifie le modèle grâce à la clé 'method'
GetDeviceInfoUnion = Annotated[
    Union[SSHGetDeviceInfo],
    Field(discriminator="method")
]


class GetRequest(BaseModel):
    """
    Requête pour la récupération de configuration.
    Implémente le principe GRASP : Information Expert (contient toutes les informations nécessaires).
    """
    getting_device_info: GetDeviceInfoUnion


class GetResponse(BaseModel):
    """
    Réponse pour la récupération de configuration.
    Contient le SwitchState parsé directement utilisable par le frontend.
    """
    status: str
    state: dict | None = None
    error: str | None = None
