from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

# Groupes intégrés ArubaOS-CX : toujours présents, non supprimables, privilèges figés.
# Cf. doc officielle "user-group" (AOS-CX 10.14 Hardening Guide / CLI Guide).
BUILTIN_GROUPS = {"administrators", "operators", "auditors"}

MAX_LOCAL_USERS = 63  # + admin implicite = 64 max, conforme à la doc officielle
MAX_USER_GROUPS = 29
MAX_RULES_PER_GROUP = 1024


class RuleAction(str, Enum):
    PERMIT = "permit"
    DENY = "deny"


class CommandRule(BaseModel):
    """Une règle d'autorisation de commande CLI au sein d'un groupe défini par l'utilisateur."""

    seq: int = Field(..., ge=1, le=MAX_RULES_PER_GROUP)
    action: RuleAction
    command_pattern: str = Field(..., min_length=1, max_length=128)  # motif CLI, ex. "show .*"
    comment: Optional[str] = Field(default=None, max_length=64)


class UserGroup(BaseModel):
    """
    Groupe local défini par l'utilisateur. Les règles sont évaluées dans l'ordre
    croissant de `seq` ; la première correspondance fait foi (deny implicite en
    fin de liste si aucune règle ne correspond).
    """

    name: str = Field(..., min_length=1, max_length=32)
    rules: list[CommandRule] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def name_must_not_shadow_builtin(cls, v: str) -> str:
        if v in BUILTIN_GROUPS:
            raise ValueError(f"'{v}' est un groupe intégré : il ne peut pas être redéfini.")
        return v

    @field_validator("rules")
    @classmethod
    def sequence_numbers_must_be_unique(cls, v: list[CommandRule]) -> list[CommandRule]:
        seqs = [r.seq for r in v]
        if len(seqs) != len(set(seqs)):
            raise ValueError("Les numéros de séquence des règles doivent être uniques au sein d'un groupe.")
        if len(seqs) > MAX_RULES_PER_GROUP:
            raise ValueError(f"Un groupe ne peut pas dépasser {MAX_RULES_PER_GROUP} règles.")
        return v


class LocalUser(BaseModel):
    """
    Utilisateur local. 'admin' n'apparaît jamais ici : il est implicite,
    toujours présent, jamais supprimable — donc absent de l'état désiré par
    construction plutôt que protégé par un cas particulier dispersé ailleurs.
    """

    username: str = Field(..., min_length=1, max_length=32)
    group: str  # nom d'un groupe intégré ou défini par l'utilisateur
    password_plaintext: str = Field(..., min_length=1, max_length=64)

    @field_validator("username")
    @classmethod
    def username_must_not_be_admin(cls, v: str) -> str:
        if v == "admin":
            raise ValueError("'admin' est un compte implicite du switch : il ne se déclare pas dans l'état désiré.")
        return v

    @field_validator("password_plaintext")
    @classmethod
    def password_charset(cls, v: str) -> str:
        # Exigence officielle AOS-CX : ASCII imprimable 0x21-0x7E uniquement.
        if not all(0x21 <= ord(c) <= 0x7E for c in v):
            raise ValueError("Le mot de passe ne peut contenir que des caractères ASCII imprimables (pas d'espace).")
        return v
