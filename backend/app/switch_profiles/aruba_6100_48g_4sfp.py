from app.switch_profiles.base import PortDefinition, PortLayout, PortMedium, SwitchProfile

SFP_COUNT = 4

PORT_SPACING_X = 34
ROW_TOP_Y = 40
ROW_BOTTOM_Y = 80
START_X = 20


def _build_copper_ports(copper_count: int) -> list[PortDefinition]:
    """N ports RJ45 en quinconce : impairs en rangée haute, pairs en rangée basse."""
    ports: list[PortDefinition] = []
    for i in range(1, copper_count + 1):
        pair_column = (i + 1) // 2 - 1
        is_odd = i % 2 == 1
        ports.append(
            PortDefinition(
                id=f"1/1/{i}",
                index=i,
                medium=PortMedium.RJ45,
                layout=PortLayout(
                    x=START_X + pair_column * PORT_SPACING_X,
                    y=ROW_TOP_Y if is_odd else ROW_BOTTOM_Y,
                ),
            )
        )
    return ports


def _build_sfp_ports(copper_count: int) -> list[PortDefinition]:
    """4 ports SFP+, regroupés à droite du panneau, numérotés à la suite des ports cuivre."""
    ports: list[PortDefinition] = []
    base_x = START_X + (copper_count / 2) * PORT_SPACING_X + 40
    for i in range(SFP_COUNT):
        port_number = copper_count + i + 1
        ports.append(
            PortDefinition(
                id=f"1/1/{port_number}",
                index=port_number,
                medium=PortMedium.SFP_PLUS,
                layout=PortLayout(
                    x=base_x + (i % 2) * PORT_SPACING_X,
                    y=ROW_TOP_Y if i < 2 else ROW_BOTTOM_Y,
                ),
            )
        )
    return ports


def build_aruba_6100_profile(copper_count: int, model_name: str) -> SwitchProfile:
    """
    Constructeur générique pour la famille Aruba 6100 (4SFP+). Toutes les
    variantes (12G/24G/48G) partagent la même disposition et les mêmes
    capacités — seul le nombre de ports cuivre change.
    """
    return SwitchProfile(
        vendor_os="aoscx",
        model=model_name,
        ports=_build_copper_ports(copper_count) + _build_sfp_ports(copper_count),
        # Confirmé par le guide officiel "AOS-CX 10.13 Layer-2 Bridging Guide —
        # 4100i, 6000, 6100, 6200 Switch Series" : "All interfaces are
        # non-routed (Layer 2) by default when created." Contrairement aux
        # chassis 83xx/84xx, cette famille ne nécessite PAS "no routing"
        # avant vlan access/trunk.
        requires_no_routing=False,
        max_vlan_id=4094,
        reserved_vlan_ids=[1],
        max_user_created=64,
    )


ARUBA_6100_48G_4SFP = build_aruba_6100_profile(48, "Aruba 6100 48G 4SFP+ (JL678A)")
ARUBA_6100_24G_4SFP = build_aruba_6100_profile(24, "Aruba 6100 24G 4SFP+ (JL676A)")

# ⚠️ Numérotation des ports SFP+ posée par convention, cohérente avec les
# schémas Aruba habituels, à vérifier sur le boîtier réel (`show interface
# brief`) avant tout usage en production — non vérifiable depuis ce sandbox.
