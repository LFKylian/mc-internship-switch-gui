from __future__ import annotations

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


class Vlan(BaseModel):
    id: int = Field(..., ge=1, le=4094)
    name: str = Field(..., min_length=1, max_length=32)
    description: Optional[str] = None


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
