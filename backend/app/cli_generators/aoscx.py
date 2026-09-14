from __future__ import annotations

from app.domain.users import BUILTIN_GROUPS
from app.domain.state_diff import DELETION_MARK

from app.switch_profiles.base import SwitchProfile
from app.cli_generators.base import ConfigOutputGenerator
from app.domain.models import Port, PortMode, SwitchState, Vlan


class AosCxCliGenerator(ConfigOutputGenerator):
    """
    Traduit un état désiré complet (VLANs + ports) en commandes CLI AOS-CX
    permettant de l'atteindre sur un switch en configuration usine (vide).

    Décrit l'état cible dans son intégralité — pas de calcul de diff — ce qui
    est correct et suffisant tant que l'hypothèse "switch vierge" tient.
    L'import d'un état existant (diff par rapport à l'état réel) sera traité
    séparément plus tard, sans modifier cette classe.
    """

    def generate(self, profile: SwitchProfile, state: SwitchState) -> str:
        state_diff: SwitchState = ConfigOutputGenerator.getStateDiff(state)

        lines: list[str] = ["configure terminal"]
        lines.extend(self._vlan_lines(profile, state_diff))
        lines.extend(self._user_group_lines(state_diff))
        lines.extend(self._user_lines(state_diff))
        lines.extend(self._interface_lines(profile, state_diff))
        lines.append("    exit")  # quitte le mode configuration globale
        return "\n".join(lines)

    def _user_group_lines(self, state: SwitchState) -> list[str]:
        lines: list[str] = []
        groups = state.user_groups
        for key in groups:
            if DELETION_MARK in key:
                lines.append(f"    no user-group {groups[key].name}")
            else:
                lines.append(f"    user-group {groups[key].name}")
                for rule in sorted(groups[key].rules, key=lambda r: r.seq):
                    if rule.comment:
                        lines.append(f"        {rule.seq} comment {rule.comment}")
                    lines.append(f'        {rule.seq} {rule.action.value} cli command "{rule.command_pattern}"')
                lines.append("        exit")
        return lines

    def _user_lines(self, state: SwitchState) -> list[str]:
        lines: list[str] = []
        users = state.users
        for key in users:
            if DELETION_MARK in key:
                lines.append(f"    no user {users[key].username}")
            else:
                if f"{DELETION_MARK}{users[key].group}" in state.user_groups.keys():
                    lines.append(f"    user {users[key].username} group {BUILTIN_GROUPS[0]} password plaintext {users[key].password_plaintext}")
                else:
                    lines.append(f"    user {users[key].username} group {users[key].group} password plaintext {users[key].password_plaintext}")
        return lines

    def _vlan_lines(self, profile: SwitchProfile, state: SwitchState) -> list[str]:
        lines: list[str] = []
        vlans = sorted(
            (v for v in state.vlans.values() if v.id not in profile.reserved_vlan_ids),
            key=lambda v: v.id,
        )
        for vlan in vlans:
            if vlan.description == DELETION_MARK:
                lines.append(f"    no vlan {vlan.id}")
            else:
                lines.append(f"    vlan {vlan.id}")
                lines.append(f"        name {vlan.name}")
                if vlan.description:
                    lines.append(f"        description {vlan.description}")
                lines.append("        exit")
                lines.extend(self._interface_vlan_lines(vlan))
        return lines

    def _interface_vlan_lines(self, vlan: Vlan) -> list[str]:
        lines: list[str] = []
        if vlan.ip_interface:
            vlan_interface = vlan.ip_interface
            lines.append(f"    interface vlan {vlan.id}")
            lines.append(f"        ip address {vlan_interface.ip}/{vlan_interface.mask}")
            lines.append("        exit")
        return lines

    def _interface_lines(self, profile: SwitchProfile, state: SwitchState) -> list[str]:
        lines: list[str] = []
        known_ids = profile.port_ids()
        ports = sorted(
            (p for p in state.ports.values() if p.id in known_ids),
            key=self._port_sort_key,
        )
        for port in ports:
            lines.append(f"    interface {port.id}")

            if profile.requires_no_routing:
                # Uniquement sur les familles où les ports sont L3 par défaut
                # (ex. 83xx/84xx). Sur le 6100 (requires_no_routing=False),
                # les ports sont déjà L2 : cette ligne est omise, volontairement.
                lines.append("        no routing")

            lines.append("        no shutdown" if port.enabled else "        shutdown")

            if port.description:
                lines.append(f"        description {port.description}")

            if port.mode == PortMode.ACCESS:
                lines.append(f"        vlan access {port.native_vlan}")
            else:
                lines.append(f"        vlan trunk native {port.native_vlan}")
                if port.tagged_vlans:
                    tagged = ",".join(str(v) for v in sorted(port.tagged_vlans))
                    lines.append(f"        vlan trunk allowed {tagged}")

            lines.append("        exit")
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
