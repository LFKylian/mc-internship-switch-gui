"""
Scénario de test manuel (pas un test unitaire formel — juste une vérification
rapide, à la main, de bout en bout) :

- Création de 2 VLANs : 10 (SERVEURS), 20 (POSTES)
- Port 1/1/1 en access, VLAN 10
- Port 1/1/2 en access, VLAN 20
- Port 1/1/49 (SFP+) en trunk, natif VLAN 1, tagué 10 et 20 (typiquement un uplink)
- Port 1/1/5 laissé à l'état par défaut : ne doit PAS apparaître dans le CLI
"""

from app.domain.models import Port, PortMode, SwitchState, Vlan
from app.cli_generators.aoscx import AosCxCliGenerator
from app.switch_profiles.aruba_6100_48g_4sfp import ARUBA_6100_48G_4SFP

state = SwitchState(
    vlans={
        10: Vlan(id=10, name="SERVEURS"),
        20: Vlan(id=20, name="POSTES"),
    },
    ports={
        "1/1/1": Port(id="1/1/1", mode=PortMode.ACCESS, native_vlan=10),
        "1/1/2": Port(id="1/1/2", mode=PortMode.ACCESS, native_vlan=20),
        "1/1/49": Port(
            id="1/1/49",
            mode=PortMode.TRUNK,
            native_vlan=1,
            tagged_vlans=[10, 20],
        ),
        "1/1/5": Port(id="1/1/5"),  # état par défaut, doit être omis
    },
)

cli = AosCxCliGenerator().generate(ARUBA_6100_48G_4SFP, state)
print(cli)

assert "1/1/5" not in cli, "Un port resté à l'état par défaut ne doit pas apparaître dans le CLI"
assert "vlan 10" in cli and "vlan 20" in cli
assert "vlan access 10" in cli
assert "vlan trunk allowed 10,20" in cli
assert "no routing" not in cli, "Le 6100 ne doit pas générer 'no routing'"
print("\n--- Assertions OK ---")
