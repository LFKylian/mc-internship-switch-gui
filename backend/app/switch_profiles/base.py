from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PortMedium(str, Enum):
    RJ45 = "rj45"
    SFP_PLUS = "sfp+"


class PortLayout(BaseModel):
    """Position du port sur le schéma SVG. Propriété du modèle physique, pas de l'état logique."""

    x: float
    y: float


class PortDefinition(BaseModel):
    """Description matérielle et immuable d'un port (ce que le port EST, pas comment il est configuré)."""

    id: str
    index: int
    medium: PortMedium
    layout: PortLayout


class SwitchProfile(BaseModel):
    """
    Catalogue de capacités d'un modèle de switch (GRASP Information Expert).
    Toute variation de comportement liée au matériel ou à la famille d'OS doit
    être un champ ICI, jamais un `if` dispersé dans le générateur CLI.
    """

    vendor_os: str  # "aoscx" | "aos-switch" ...
    model: str
    ports: list[PortDefinition]
    # true si les ports sont L3 (routés) par défaut et nécessitent `no routing`
    # avant vlan access/trunk (chassis 83xx/84xx). false si déjà L2 par défaut.
    requires_no_routing: bool
    max_vlan_id: int = 4094
    reserved_vlan_ids: list[int] = Field(default_factory=lambda: [1])

    def port_ids(self) -> set[str]:
        return {p.id for p in self.ports}
