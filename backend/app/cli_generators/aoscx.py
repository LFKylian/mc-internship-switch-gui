from __future__ import annotations

from app.cli_generators.base import ConfigOutputGenerator
from app.domain.models import Port, PortMode, SwitchState
from app.switch_profiles.base import SwitchProfile


class AosCxCliGenerator(ConfigOutputGenerator):
    """
    Traduit un état désiré complet (VLANs + ports) en commandes CLI AOS-CX
    permettant de l'atteindre sur un switch.

    Si current_state est fourni, génère uniquement les commandes pour passer
    de current_state à state (diff). Sinon, génère toutes les commandes pour
    passer de l'état usine à state.
    """

    def generate(self, profile: SwitchProfile, state: SwitchState, current_state: SwitchState | None = None) -> str:
        lines: list[str] = ["configure terminal"]
        
        if current_state is not None:
            # Mode diff: générer uniquement les commandes pour passer de current_state à state
            lines.extend(self._vlan_lines_diff(profile, current_state, state))
            lines.extend(self._user_group_lines_diff(current_state, state))
            lines.extend(self._user_lines_diff(current_state, state))
            lines.extend(self._interface_lines_diff(profile, current_state, state))
        else:
            # Mode complet: générer toutes les commandes pour passer de l'état usine à state
            lines.extend(self._vlan_lines(profile, state))
            lines.extend(self._user_group_lines(state))
            lines.extend(self._user_lines(state))
            lines.extend(self._interface_lines(profile, state))
        
        lines.append("exit")  # quitte le mode configuration globale
        return "\n".join(lines)

    def _user_group_lines(self, state: SwitchState) -> list[str]:
        lines: list[str] = []
        groups = sorted(state.user_groups.values(), key=lambda g: g.name)
        for group in groups:
            lines.append(f"user-group {group.name}")
            for rule in sorted(group.rules, key=lambda r: r.seq):
                if rule.comment:
                    lines.append(f"    {rule.seq} comment {rule.comment}")
                lines.append(f'    {rule.seq} {rule.action.value} cli command "{rule.command_pattern}"')
            lines.append("    exit")
        return lines

    def _user_lines(self, state: SwitchState) -> list[str]:
        lines: list[str] = []
        users = sorted(state.users.values(), key=lambda u: u.username)
        for user in users:
            lines.append(f"user {user.username} group {user.group} password plaintext {user.password_plaintext}")
        return lines

    def _vlan_lines(self, profile: SwitchProfile, state: SwitchState) -> list[str]:
        lines: list[str] = []
        vlans = sorted(
            (v for v in state.vlans.values() if v.id not in profile.reserved_vlan_ids),
            key=lambda v: v.id,
        )
        for vlan in vlans:
            lines.append(f"vlan {vlan.id}")
            lines.append(f"    name {vlan.name}")
            if vlan.description:
                lines.append(f"    description {vlan.description}")
            lines.append("    exit")
        return lines

    def _interface_lines(self, profile: SwitchProfile, state: SwitchState) -> list[str]:
        lines: list[str] = []
        known_ids = profile.port_ids()
        ports = sorted(
            (p for p in state.ports.values() if p.id in known_ids and self._is_non_default(p)),
            key=self._port_sort_key,
        )
        for port in ports:
            lines.append(f"interface {port.id}")

            if profile.requires_no_routing:
                # Uniquement sur les familles où les ports sont L3 par défaut
                # (ex. 83xx/84xx). Sur le 6100 (requires_no_routing=False),
                # les ports sont déjà L2 : cette ligne est omise, volontairement.
                lines.append("    no routing")

            lines.append("    no shutdown" if port.enabled else "    shutdown")

            if port.description:
                lines.append(f"    description {port.description}")

            if port.mode == PortMode.ACCESS:
                lines.append(f"    vlan access {port.native_vlan}")
            else:
                lines.append(f"    vlan trunk native {port.native_vlan}")
                if port.tagged_vlans:
                    tagged = ",".join(str(v) for v in sorted(port.tagged_vlans))
                    lines.append(f"    vlan trunk allowed {tagged}")

            lines.append("    exit")
        return lines

    @staticmethod
    def _is_non_default(port: Port) -> bool:
        is_default_access_vlan1 = port.mode == PortMode.ACCESS and port.native_vlan == 1
        return (
            not port.enabled
            or bool(port.description)
            or not is_default_access_vlan1
            or (port.mode == PortMode.TRUNK and bool(port.tagged_vlans))
        )

    @staticmethod
    def _port_sort_key(port: Port) -> tuple[int, int, int]:
        parts = port.id.split("/")
        return int(parts[0]), int(parts[1]), int(parts[2])

    # ===== Méthodes pour la génération de diff =====

    def _vlan_lines_diff(self, profile: SwitchProfile, current_state: SwitchState, desired_state: SwitchState) -> list[str]:
        """Génère les commandes pour créer/mettre à jour/supprimer les VLANs."""
        lines: list[str] = []
        
        current_vlan_ids = set(current_state.vlans.keys())
        desired_vlan_ids = set(desired_state.vlans.keys())
        
        # VLANs à créer ou mettre à jour
        for vlan_id in sorted(desired_vlan_ids):
            if vlan_id in profile.reserved_vlan_ids:
                continue
            
            desired_vlan = desired_state.vlans[vlan_id]
            current_vlan = current_state.vlans.get(vlan_id)
            
            if current_vlan is None:
                # VLAN n'existe pas, il faut le créer
                lines.append(f"vlan {vlan_id}")
                lines.append(f"    name {desired_vlan.name}")
                if desired_vlan.description:
                    lines.append(f"    description {desired_vlan.description}")
                lines.append("    exit")
            elif current_vlan != desired_vlan:
                # VLAN existe mais a changé, il faut le mettre à jour
                lines.append(f"vlan {vlan_id}")
                lines.append(f"    name {desired_vlan.name}")
                if desired_vlan.description:
                    lines.append(f"    description {desired_vlan.description}")
                else:
                    # Supprimer la description si elle existe
                    lines.append("    no description")
                lines.append("    exit")
        
        # VLANs à supprimer (présents dans current mais pas dans desired)
        # Note: On ne supprime pas les VLANs utilisés par des ports
        vlan_used_in_desired = set()
        for port in desired_state.ports.values():
            vlan_used_in_desired.add(port.native_vlan)
            vlan_used_in_desired.update(port.tagged_vlans)
        
        for vlan_id in sorted(current_vlan_ids - desired_vlan_ids):
            if vlan_id not in vlan_used_in_desired and vlan_id not in profile.reserved_vlan_ids:
                lines.append(f"no vlan {vlan_id}")
        
        return lines

    def _user_group_lines_diff(self, current_state: SwitchState, desired_state: SwitchState) -> list[str]:
        """Génère les commandes pour créer/mettre à jour/supprimer les groupes d'utilisateurs."""
        lines: list[str] = []
        
        current_group_names = set(current_state.user_groups.keys())
        desired_group_names = set(desired_state.user_groups.keys())
        
        # Groupes à créer ou mettre à jour
        for group_name in sorted(desired_group_names):
            desired_group = desired_state.user_groups[group_name]
            current_group = current_state.user_groups.get(group_name)
            
            if current_group is None:
                # Groupe n'existe pas, il faut le créer
                lines.append(f"user-group {group_name}")
                for rule in sorted(desired_group.rules, key=lambda r: r.seq):
                    if rule.comment:
                        lines.append(f"    {rule.seq} comment {rule.comment}")
                    lines.append(f'    {rule.seq} {rule.action.value} cli command "{rule.command_pattern}"')
                lines.append("    exit")
            elif current_group != desired_group:
                # Groupe existe mais a changé, il faut le mettre à jour
                lines.append(f"user-group {group_name}")
                # Supprimer toutes les règles existantes et recréer
                # (AOS-CX ne permet pas de supprimer des règles individuelles facilement)
                for rule in sorted(desired_group.rules, key=lambda r: r.seq):
                    if rule.comment:
                        lines.append(f"    {rule.seq} comment {rule.comment}")
                    lines.append(f'    {rule.seq} {rule.action.value} cli command "{rule.command_pattern}"')
                lines.append("    exit")
        
        # Groupes à supprimer
        for group_name in sorted(current_group_names - desired_group_names):
            lines.append(f"no user-group {group_name}")
        
        return lines

    def _user_lines_diff(self, current_state: SwitchState, desired_state: SwitchState) -> list[str]:
        """Génère les commandes pour créer/mettre à jour/supprimer les utilisateurs."""
        lines: list[str] = []
        
        current_user_names = set(current_state.users.keys())
        desired_user_names = set(desired_state.users.keys())
        
        # Utilisateurs à créer ou mettre à jour
        for username in sorted(desired_user_names):
            desired_user = desired_state.users[username]
            current_user = current_state.users.get(username)
            
            if current_user is None:
                # Utilisateur n'existe pas, il faut le créer
                lines.append(f"user {username} group {desired_user.group} password plaintext {desired_user.password_plaintext}")
            elif current_user != desired_user:
                # Utilisateur existe mais a changé, il faut le mettre à jour
                lines.append(f"user {username} group {desired_user.group} password plaintext {desired_user.password_plaintext}")
        
        # Utilisateurs à supprimer
        for username in sorted(current_user_names - desired_user_names):
            lines.append(f"no user {username}")
        
        return lines

    def _interface_lines_diff(self, profile: SwitchProfile, current_state: SwitchState, desired_state: SwitchState) -> list[str]:
        """Génère les commandes pour configurer les ports qui ont changé."""
        lines: list[str] = []
        known_ids = profile.port_ids()
        
        # Trouver tous les ports qui existent dans desired_state
        # On inclut à la fois les ports modifiés et les nouveaux ports
        desired_port_ids = set(desired_state.ports.keys())
        
        for port_id in sorted(desired_port_ids, key=lambda pid: self._port_sort_key(desired_state.ports[pid])):
            if port_id not in known_ids:
                continue
            
            current_port = current_state.ports.get(port_id)
            desired_port = desired_state.ports[port_id]
            
            if current_port is None:
                # Nouveau port - générer toutes les commandes de configuration
                lines.append(f"interface {port_id}")
                
                if profile.requires_no_routing:
                    lines.append("    no routing")
                
                if not desired_port.enabled:
                    lines.append("    shutdown")
                else:
                    lines.append("    no shutdown")
                
                if desired_port.description:
                    lines.append(f"    description {desired_port.description}")
                
                if desired_port.mode == PortMode.ACCESS:
                    lines.append(f"    vlan access {desired_port.native_vlan}")
                else:
                    lines.append(f"    vlan trunk native {desired_port.native_vlan}")
                    if desired_port.tagged_vlans:
                        tagged = ",".join(str(v) for v in sorted(desired_port.tagged_vlans))
                        lines.append(f"    vlan trunk allowed {tagged}")
                
                lines.append("    exit")
            else:
                # Port existant - vérifier si le port a changé
                if not self._ports_are_identical(current_port, desired_port):
                    lines.append(f"interface {port_id}")
                    
                    if profile.requires_no_routing:
                        lines.append("    no routing")
                    
                    # Gérer l'état enabled/shutdown
                    if desired_port.enabled != current_port.enabled:
                        lines.append("    no shutdown" if desired_port.enabled else "    shutdown")
                    
                    # Gérer la description
                    if desired_port.description != current_port.description:
                        if desired_port.description:
                            lines.append(f"    description {desired_port.description}")
                        else:
                            lines.append("    no description")
                    
                    # Gérer le mode et les VLANs
                    if desired_port.mode != current_port.mode:
                        if desired_port.mode == PortMode.ACCESS:
                            lines.append(f"    vlan access {desired_port.native_vlan}")
                        else:
                            lines.append(f"    vlan trunk native {desired_port.native_vlan}")
                            if desired_port.tagged_vlans:
                                tagged = ",".join(str(v) for v in sorted(desired_port.tagged_vlans))
                                lines.append(f"    vlan trunk allowed {tagged}")
                    else:
                        # Même mode, vérifier les VLANs
                        if desired_port.mode == PortMode.ACCESS:
                            if desired_port.native_vlan != current_port.native_vlan:
                                lines.append(f"    vlan access {desired_port.native_vlan}")
                        else:
                            # Mode trunk
                            if desired_port.native_vlan != current_port.native_vlan:
                                lines.append(f"    vlan trunk native {desired_port.native_vlan}")
                            
                            # Gérer les tagged VLANs
                            current_tagged = set(current_port.tagged_vlans)
                            desired_tagged = set(desired_port.tagged_vlans)
                            
                            if desired_tagged != current_tagged:
                                if desired_tagged:
                                    tagged = ",".join(str(v) for v in sorted(desired_tagged))
                                    lines.append(f"    vlan trunk allowed {tagged}")
                                else:
                                    lines.append("    no vlan trunk allowed")
                    
                    lines.append("    exit")
        
        return lines

    @staticmethod
    def _ports_are_identical(port1: Port, port2: Port) -> bool:
        """Compare deux ports et retourne True s'ils sont identiques."""
        return (
            port1.enabled == port2.enabled and
            port1.mode == port2.mode and
            port1.native_vlan == port2.native_vlan and
            set(port1.tagged_vlans) == set(port2.tagged_vlans) and
            port1.description == port2.description
        )
