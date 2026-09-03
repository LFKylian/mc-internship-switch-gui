from __future__ import annotations

from app.cli_generators.base import ConfigOutputGenerator
from app.domain.models import Port, PortMode, SwitchState
from app.switch_profiles.base import SwitchProfile


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
        lines: list[str] = ["configure terminal"]
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
