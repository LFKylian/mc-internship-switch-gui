from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


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


# ===============================================================================
# GESTION DES UTILISATEURS ET DES GROUPES
# ===============================================================================

class Group(BaseModel):
    name: str = Field(..., min_length=1, max_length=32)
    sub_command: str


class User(BaseModel):
    name: str = Field(..., min_length=1, max_length=32, pattern=r'^[A-Za-z0-9\-\.\_]+$')
    password: str
    group: Group

    @field_validator('name')
    @classmethod
    def exclude_forbidden(cls, v: str) -> str:
        forbidden_words =   ["admin", "root", "remote_user",
                            "daemon", "bin", "sys", "sync", "proxy", "www-data", "backup", 
                            "list", "irc", "gnats", "nobody", "systemd-bus-proxy", "sshd",
                            "messagebus", "rpc", "systemd-journal-gateway", "systemd-journal-remote",
                            "systemd-journalupload", "systemd-timesync", "systemd-coredump",
                            "systemd-resolve", "rpcuser", "vagrant", "opsd", "rdanet", "_lldpd",
                            "rdaadmin", "rdaweb", "docker_container", "tss"
                            ]
        if any(word == v.lower().replace(" ","") for word in forbidden_words):
            raise ValueError("name contains forbidden words")
        return v