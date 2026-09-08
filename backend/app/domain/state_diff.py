"""
Module pour calculer les différences entre deux états de switch et générer
uniquement les commandes CLI nécessaires pour passer de l'état actuel à l'état souhaité.
"""

from __future__ import annotations

from typing import Optional

from app.domain.users import LocalUser, UserGroup
from app.switch_profiles.base import SwitchProfile
from app.domain.models import Port, PortMode, SwitchState


DELETION_MARK: str = "__DELETE__"

def compute_state_diff(base_state: SwitchState, desired_state: SwitchState) -> SwitchState:
    """
    Calcule la différence entre l'état actuel et l'état souhaité.
    
    Retourne un SwitchState minimal contenant uniquement les éléments qui diffèrent,
    avec des valeurs spéciales pour indiquer les suppressions.
    
    Pour les VLANs :
    - Un VLAN présent dans desired_state mais pas dans base_state doit être créé
    - Un VLAN présent dans base_state mais pas dans desired_state doit être supprimé
    
    Pour les ports :
    - Seuls les ports qui ont des différences sont inclus
    - Les valeurs null dans le port indiquent "réinitialiser à la valeur par défaut"
    
    Pour les utilisateurs et groupes : même logique.
    """
    diff_state = SwitchState()

    # Calcul des différences pour les VLANs
    base_vlan_ids = set(base_state.vlans.keys())
    desired_vlan_ids = set(desired_state.vlans.keys())

    # VLANs à créer ou modifier
    for vlan_id in desired_vlan_ids:
        if (vlan_id not in base_vlan_ids) or (desired_state.vlans[vlan_id] != base_state.vlans[vlan_id]):
            # VLAN n'existe pas, il faut le créer
            # ou VLAN existe mais a changé, il faut le mettre à jour
            diff_state.vlans[vlan_id] = desired_state.vlans[vlan_id]

    # VLANs à supprimer (présents dans base mais pas dans desired)
    # On peut utiliser un VLAN avec id=-1 comme marqueur de suppression
    # Mais pour l'instant, on ne gère pas la suppression de VLANs utilisés
    # (c'est complexe car il faut vérifier qu'aucun port ne l'utilise)

    # Calcul des différences pour les ports
    all_port_ids = set(base_state.ports.keys()) | set(desired_state.ports.keys())

    for port_id in all_port_ids:
        base_port = base_state.ports.get(port_id)
        desired_port = desired_state.ports.get(port_id)

        if desired_port is None:
            # Port doit être supprimé - on le marque avec un port désactivé
            # Mais en pratique, on ne peut pas supprimer un port, juste le désactiver
            continue

        if base_port is None:
            # Port n'existe pas dans l'état actuel, il faut le configurer
            diff_state.ports[port_id] = desired_port
        else:
            # Comparer les attributs du port
            port_diff = _compare_ports(base_port, desired_port)
            if port_diff is not None:
                diff_state.ports[port_id] = port_diff

    # Calcul des différences pour les utilisateurs
    base_user_names = set(base_state.users.keys())
    desired_user_names = set(desired_state.users.keys())

    for username in desired_user_names:
        if username not in base_user_names:
            diff_state.users[username] = desired_state.users[username]
        elif desired_state.users[username] != base_state.users[username]:
            diff_state.users[username] = desired_state.users[username]

    # Utilisateurs à supprimer
    for username in base_user_names - desired_user_names:
        # On marque pour suppression - en CLI AOS-CX, on utilise "no user <username>"
        # Pour l'instant, on inclut l'utilisateur avec un marqueur spécial
        diff_state.users[f"{DELETION_MARK}{username}"] = LocalUser(
            username=username,
            group="x",
            password_plaintext="x"
        )

    # Calcul des différences pour les groupes d'utilisateurs
    base_group_names = set(base_state.user_groups.keys())
    desired_group_names = set(desired_state.user_groups.keys())

    for group_name in desired_group_names:
        if group_name not in base_group_names:
            diff_state.user_groups[group_name] = desired_state.user_groups[group_name]
        elif desired_state.user_groups[group_name] != base_state.user_groups[group_name]:
            diff_state.user_groups[group_name] = desired_state.user_groups[group_name]

    # Groupes à supprimer
    for group_name in base_group_names - desired_group_names:
        diff_state.user_groups[f"{DELETION_MARK}{group_name}"] = UserGroup(
            name=group_name,
            rules=[]
        )
    return diff_state


def _compare_ports(base: Port, desired: Port) -> Optional[Port]:
    """
    Compare deux ports et retourne un port représentant les différences,
    ou None s'ils sont identiques.
    """
    if (base.enabled == desired.enabled and
        base.mode == desired.mode and
        base.native_vlan == desired.native_vlan and
        set(base.tagged_vlans) == set(desired.tagged_vlans) and
        base.description == desired.description):
        return None

    # Il y a des différences, retourner le port souhaité
    return desired


# def create_empty_state_from_profile(profile: SwitchProfile) -> SwitchState:
#     """
#     Crée un état vide (usine) à partir d'un profil de switch.
    
#     C'est l'état par défaut : tous les ports en mode access sur VLAN 1,
#     activés, sans description.
#     """

#     ports = {}
#     for port_def in profile.ports:
#         ports[port_def.id] = Port(
#             id=port_def.id,
#             enabled=True,
#             mode=PortMode.ACCESS,
#             native_vlan=1,
#             tagged_vlans=[],
#             description=None
#         )

#     return SwitchState(
#         vlans={},
#         ports=ports,
#         users={},
#         user_groups={}
#     )