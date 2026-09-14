from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.domain.users import (
    BUILTIN_GROUPS,
    MAX_LOCAL_USERS,
    MAX_USER_GROUPS,
    LocalUser,
    UserGroup,
)


class PortMode(str, Enum):
    ACCESS = "access"
    TRUNK = "trunk"


class IpAddress(BaseModel):
    ip: str
    mask: str

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        match = re.match(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", v)
        if not match:
            raise ValueError("Format de l'adresse IP invalide.")

        octets = [int(match.group(i)) for i in range(1, 5)]

        for i, octet in enumerate(octets):
            if octet < 0 or octet > 255:
                raise ValueError("Chaque octet doit être compris entre 0 et 255.")
            if i == 3 and (octet == 0 or octet == 255):
                raise ValueError("Le dernier octet ne peut pas être 0 ou 255.")

        return v

    @field_validator("mask")
    @classmethod
    def validate_mask(cls, v: str) -> str:
        try:
            mask_val = int(v)
            if not (1 <= mask_val <= 32):
                raise ValueError("Le masque doit être compris entre 1 et 32.")
        except ValueError:
            raise ValueError("Valeur du masque non reconnue.")

        return v


class Vlan(BaseModel):
    id: int = Field(..., ge=1, le=4094)
    name: str = Field(..., min_length=1, max_length=32)
    description: Optional[str] = None
    ip_interface: Optional[IpAddress] = Field(default=None)


class Port(BaseModel):
    """État logique configurable d'un port (ce que l'utilisateur choisit dans la GUI)."""

    id: str  # ex: "1/1/1"
    enabled: bool = True
    mode: PortMode = PortMode.ACCESS
    native_vlan: int = 1  # VLAN d'accès si ACCESS, VLAN natif si TRUNK
    tagged_vlans: list[int] = Field(default_factory=list)  # trunk uniquement
    description: Optional[str] = None

    @field_validator("tagged_vlans")
    @classmethod
    def tagged_vlans_must_not_include_native(cls, v: list[int], info):
        native = info.data.get("native_vlan")
        if native is not None and native in v:
            raise ValueError(
                "Un VLAN ne peut pas être à la fois natif/access et tagué sur le même port."
            )
        return v

    @field_validator("tagged_vlans")
    @classmethod
    def tagged_vlans_only_meaningful_in_trunk(cls, v: list[int], info):
        mode = info.data.get("mode")
        if mode == PortMode.ACCESS and v:
            raise ValueError("tagged_vlans doit être vide en mode access.")
        return v


class SwitchState(BaseModel):
    """État désiré complet de la configuration logique d'un switch."""

    vlans: dict[int, Vlan] = Field(default_factory=dict)
    ports: dict[str, Port] = Field(default_factory=dict)
    users: dict[str, LocalUser] = Field(default_factory=dict)
    user_groups: dict[str, UserGroup] = Field(default_factory=dict)

    base_state: Optional[SwitchState] = Field(default=None)

    def set_base_state(self) -> None:
        """Sauvegarde une copie de l'état actuel comme état de base."""
        # model_copy(deep=True) fige les valeurs actuelles des dictionnaires et sous-modèles
        self.base_state = self.model_copy(deep=True)

    @model_validator(mode="after")
    def validate_users_and_groups(self) -> "SwitchState":
        if len(self.users) > MAX_LOCAL_USERS:
            raise ValueError(f"Maximum {MAX_LOCAL_USERS} utilisateurs locaux (hors admin).")
        if len(self.user_groups) > MAX_USER_GROUPS:
            raise ValueError(f"Maximum {MAX_USER_GROUPS} groupes définis par l'utilisateur.")

        known_groups = BUILTIN_GROUPS | set(self.user_groups.keys())
        for user in self.users.values():
            if user.group not in known_groups:
                raise ValueError(
                    f"L'utilisateur '{user.username}' référence le groupe inconnu '{user.group}'."
                )
        return self
