from enum import Enum
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field, SecretStr

from app.domain.models import SwitchState

 
class PushMethods(Enum):
    """Les différentes méthodes de connexion supportées."""
    SSH = "ssh"


class BaseDeviceInfo(BaseModel):
    """Informations de base pour toutes les méthodes de connexion."""
    method: str
    host: str
    username: str
    password: SecretStr

class SSHDeviceInfo(BaseDeviceInfo):
    """Informations de connexion SSH spécifiques à Netmiko."""
    method: Literal["ssh"] = "ssh" # champs discriminant
    device_type: str
    port: int = 22
    secret: SecretStr = SecretStr("")

    def to_netmiko_dict(self) -> dict:
        """Convertit le modèle en dictionnaire compatible Netmiko en déballant les SecretStr."""
        data = self.model_dump()
        data.pop("method", None)
        data["password"] = self.password.get_secret_value()
        data["secret"] = self.secret.get_secret_value()
        return data


# Union discriminée : Pydantic identifie le modèle grâce à la clé 'method'
DeviceInfoUnion = Annotated[
    Union[SSHDeviceInfo],
    Field(discriminator="method")
]

class PushRequest(BaseModel):
    state: SwitchState
    pushing_device_info: DeviceInfoUnion