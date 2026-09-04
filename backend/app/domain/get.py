from enum import Enum
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field, SecretStr


class GetMethods(Enum):
    """Les différentes méthodes de récupération de configuration supportées."""
    REST_AOSCX = "rest_aoscx"


class BaseGetDeviceInfo(BaseModel):
    """Informations de base pour toutes les méthodes de récupération."""
    method: str
    host: str
    username: str
    password: SecretStr


class RestAosCxDeviceInfo(BaseGetDeviceInfo):
    """Informations de connexion REST spécifiques à ArubaOS-CX."""
    method: Literal["rest_aoscx"] = "rest_aoscx"  # champs discriminant
    port: int = 443
    use_ssl: bool = True

    def to_pyaoscx_dict(self) -> dict:
        """Convertit le modèle en dictionnaire compatible pyaoscx en déballant les SecretStr."""
        data = self.model_dump()
        data.pop("method", None)
        data["password"] = self.password.get_secret_value()
        return data


# Union discriminée : Pydantic identifie le modèle grâce à la clé 'method'
GetDeviceInfoUnion = Annotated[
    Union[RestAosCxDeviceInfo],
    Field(discriminator="method")
]


class GetRequest(BaseModel):
    """
    Requête pour la récupération de configuration.
    Implémente le principe GRASP : Information Expert (contient toutes les informations nécessaires).
    """
    getting_device_info: GetDeviceInfoUnion
