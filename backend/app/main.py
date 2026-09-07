from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from netmiko import NetmikoTimeoutException, NetmikoAuthenticationException
from sqlalchemy.orm import Session

from app.cli_generators.aoscx import AosCxCliGenerator
from app.cli_generators.base import ConfigOutputGenerator
from app.config_pushers.factory import PusherFactory
from app.domain.push import PushRequest, BaseDeviceInfo
from app.database import get_db
from app.domain.configurations import ConfigurationRepository, SavedConfiguration
from app.domain.models import SwitchState, Port, PortMode, Vlan
from app.domain.users import LocalUser, UserGroup
from app.repositories.postgres import PostgresConfigurationRepository
from app.switch_profiles.aruba_6100_48g_4sfp import ARUBA_6100_24G_4SFP, ARUBA_6100_48G_4SFP
from app.switch_profiles.base import SwitchProfile

app = FastAPI(title="Aruba Switch Configurator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROFILES: dict[str, SwitchProfile] = {
    "aruba-6100-48g-4sfp": ARUBA_6100_48G_4SFP,
    "aruba-6100-24g-4sfp": ARUBA_6100_24G_4SFP,
}

GENERATORS: dict[str, ConfigOutputGenerator] = {
    "aoscx": AosCxCliGenerator(),
}


def get_config_repo(db: Session = Depends(get_db)) -> ConfigurationRepository:
    return PostgresConfigurationRepository(db)


def _resolve_profile(profile_id: str) -> SwitchProfile:
    profile = PROFILES.get(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profil inconnu")
    return profile


def _validate_state_against_profile(profile: SwitchProfile, state: SwitchState) -> None:
    """
    Garde-fou d'intégrité partagé entre génération CLI et sauvegarde : un état
    désiré ne doit jamais référencer des ports absents du profil déclaré.
    Centralisé ici pour que save_configuration et generate_cli ne divergent
    pas silencieusement sur cette règle.
    """
    unknown_ports = set(state.ports) - profile.port_ids()
    if unknown_ports:
        raise HTTPException(
            status_code=422,
            detail=f"Ports inconnus pour ce profil : {sorted(unknown_ports)}",
        )


# --- Routes API ---

@app.get("/api/profiles")
def list_profiles() -> dict[str, str]:
    return {key: profile.model for key, profile in PROFILES.items()}


@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: str) -> SwitchProfile:
    return _resolve_profile(profile_id)


@app.post("/api/profiles/{profile_id}/generate-cli")
def generate_cli(profile_id: str, state: SwitchState, current_state: SwitchState | None = None) -> dict[str, str]:
    """
    Génère les commandes CLI pour configurer un switch.
    
    Si current_state est fourni, génère uniquement les commandes pour passer
    de current_state à state (diff). Sinon, génère toutes les commandes pour
    passer de l'état usine à state.
    """
    profile = _resolve_profile(profile_id)
    _validate_state_against_profile(profile, state)
    
    if current_state is not None:
        _validate_state_against_profile(profile, current_state)
    
    generator = GENERATORS[profile.vendor_os]
    return {"cli": generator.generate(profile, state, current_state)}


@app.post("/api/profiles/{profile_id}/fetch-current-state", status_code=status.HTTP_200_OK)
def fetch_current_state(profile_id: str, device_info: BaseDeviceInfo) -> dict[str, SwitchState]:
    """
    Récupère l'état actuel d'un switch réel via SSH.
    
    Cette fonction se connecte au switch et récupère sa configuration actuelle
    pour permettre le calcul de diff lors du push.
    """
    from app.config_pushers.factory import PusherFactory
    from netmiko import ConnectHandler
    import re
    
    profile = _resolve_profile(profile_id)
    
    # Convertir device_info en dictionnaire Netmiko
    if isinstance(device_info, dict):
        netmiko_args = device_info
    else:
        netmiko_args = device_info.model_dump()
    
    netmiko_args.pop("method", None)
    if hasattr(device_info, 'password'):
        netmiko_args["password"] = device_info.password.get_secret_value() if hasattr(device_info.password, 'get_secret_value') else device_info.password
    if hasattr(device_info, 'secret') and 'secret' in netmiko_args:
        netmiko_args["secret"] = device_info.secret.get_secret_value() if hasattr(device_info.secret, 'get_secret_value') else device_info.secret
    
    try:
        with ConnectHandler(**netmiko_args) as net_connect:
            # Récupérer la configuration actuelle
            output = net_connect.send_command("show running-config")
            
            # Parser la configuration pour extraire l'état actuel
            current_state = _parse_aoscx_config_to_state(profile, output)
            
        return {"current_state": current_state.model_dump() if hasattr(current_state, 'model_dump') else current_state}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erreur lors de la récupération de l'état actuel: {str(e)}"
        )


def _parse_aoscx_config_to_state(profile: SwitchProfile, config_output: str) -> SwitchState:
    """
    Parse la sortie de 'show running-config' d'un switch AOS-CX pour extraire l'état actuel.
    
    Note: Cette implémentation est basique et peut nécessiter des ajustements
    selon la version exacte de AOS-CX et les variations de format de sortie.
    """
    import re
    
    state = SwitchState()
    
    # Initialiser tous les ports avec leurs valeurs par défaut
    for port_def in profile.ports:
        state.ports[port_def.id] = Port(
            id=port_def.id,
            enabled=True,
            mode=PortMode.ACCESS,
            native_vlan=1,
            tagged_vlans=[],
            description=None
        )
    
    lines = config_output.splitlines()
    current_section = None
    current_vlan = None
    current_user_group = None
    current_interface = None
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('!') or line.startswith('#'):
            continue
        
        # VLAN sections
        vlan_match = re.match(r'^vlan\s+(\d+)', line)
        if vlan_match:
            vlan_id = int(vlan_match.group(1))
            if vlan_id not in profile.reserved_vlan_ids:
                current_vlan = Vlan(id=vlan_id, name="", description=None)
                state.vlans[vlan_id] = current_vlan
                current_section = 'vlan'
            continue
        
        if current_section == 'vlan' and current_vlan:
            name_match = re.match(r'^\s+name\s+(.+)$', line)
            if name_match:
                current_vlan.name = name_match.group(1).strip()
                continue
            
            desc_match = re.match(r'^\s+description\s+(.+)$', line)
            if desc_match:
                current_vlan.description = desc_match.group(1).strip()
                continue
            
            if line.strip() == 'exit':
                current_vlan = None
                current_section = None
        
        # Interface sections
        intf_match = re.match(r'^interface\s+(\S+)', line)
        if intf_match:
            intf_id = intf_match.group(1)
            if intf_id in profile.port_ids():
                current_interface = state.ports[intf_id]
                current_section = 'interface'
            continue
        
        if current_section == 'interface' and current_interface:
            shutdown_match = re.match(r'^\s+shutdown$', line)
            if shutdown_match:
                current_interface.enabled = False
                continue
            
            no_shutdown_match = re.match(r'^\s+no\s+shutdown$', line)
            if no_shutdown_match:
                current_interface.enabled = True
                continue
            
            desc_match = re.match(r'^\s+description\s+(.+)$', line)
            if desc_match:
                current_interface.description = desc_match.group(1).strip()
                continue
            
            no_desc_match = re.match(r'^\s+no\s+description$', line)
            if no_desc_match:
                current_interface.description = None
                continue
            
            # VLAN access
            vlan_access_match = re.match(r'^\s+vlan\s+access\s+(\d+)', line)
            if vlan_access_match:
                current_interface.mode = PortMode.ACCESS
                current_interface.native_vlan = int(vlan_access_match.group(1))
                current_interface.tagged_vlans = []
                continue
            
            # VLAN trunk native
            vlan_trunk_native_match = re.match(r'^\s+vlan\s+trunk\s+native\s+(\d+)', line)
            if vlan_trunk_native_match:
                current_interface.mode = PortMode.TRUNK
                current_interface.native_vlan = int(vlan_trunk_native_match.group(1))
                continue
            
            # VLAN trunk allowed
            vlan_trunk_allowed_match = re.match(r'^\s+vlan\s+trunk\s+allowed\s+(.+)$', line)
            if vlan_trunk_allowed_match:
                current_interface.mode = PortMode.TRUNK
                tagged_vlans_str = vlan_trunk_allowed_match.group(1).strip()
                if tagged_vlans_str and tagged_vlans_str != 'none':
                    current_interface.tagged_vlans = [int(v) for v in tagged_vlans_str.split(',') if v.strip()]
                else:
                    current_interface.tagged_vlans = []
                continue
            
            if line.strip() == 'exit':
                current_interface = None
                current_section = None
        
        # User sections
        user_match = re.match(r'^user\s+(\S+)\s+group\s+(\S+)\s+password\s+\S+\s+(.+)$', line)
        if user_match:
            username = user_match.group(1)
            group = user_match.group(2)
            # Note: On ne peut pas extraire le mot de passe, on le laisse vide
            state.users[username] = LocalUser(
                username=username,
                group=group,
                password_plaintext=""  # On ne peut pas récupérer le mot de passe
            )
            continue
        
        # User-group sections
        user_group_match = re.match(r'^user-group\s+(\S+)', line)
        if user_group_match:
            group_name = user_group_match.group(1)
            if group_name not in state.user_groups:
                state.user_groups[group_name] = UserGroup(name=group_name, rules=[])
            current_user_group = state.user_groups[group_name]
            current_section = 'user-group'
            continue
        
        if current_section == 'user-group' and current_user_group:
            rule_match = re.match(r'^\s+(\d+)\s+(permit|deny)\s+cli\s+command\s+"(.+)"$', line)
            if rule_match:
                seq = int(rule_match.group(1))
                action = rule_match.group(2)
                command_pattern = rule_match.group(3)
                # Vérifier si la règle existe déjà
                if not any(r.seq == seq for r in current_user_group.rules):
                    from app.domain.users import CommandRule
                    current_user_group.rules.append(CommandRule(
                        seq=seq,
                        action=action,
                        command_pattern=command_pattern
                    ))
                continue
            
            if line.strip() == 'exit':
                current_user_group = None
                current_section = None
    
    return state


# --- API Saved Configurations ---

@app.post("/api/configurations", response_model=SavedConfiguration, status_code=status.HTTP_201_CREATED)
def save_configuration(
    config: SavedConfiguration,
    repo: ConfigurationRepository = Depends(get_config_repo),
):
    profile = _resolve_profile(config.profile_id)
    _validate_state_against_profile(profile, config.state)
    return repo.save(config)


@app.get("/api/configurations", response_model=list[SavedConfiguration])
def list_configurations(repo: ConfigurationRepository = Depends(get_config_repo)):
    return repo.list()


@app.get("/api/configurations/{config_id}", response_model=SavedConfiguration)
def get_configuration(
    config_id: int,
    repo: ConfigurationRepository = Depends(get_config_repo),
):
    config = repo.get(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Configuration non trouvée")
    return config


@app.delete("/api/configurations/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_configuration(
    config_id: int,
    repo: ConfigurationRepository = Depends(get_config_repo),
):
    success = repo.delete(config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Configuration non trouvée")


# --- API Push Configurations ---

@app.post("/api/profiles/{profile_id}/push-configuration/{modal}", status_code=status.HTTP_202_ACCEPTED)
def push_configuration(profile_id: str, modal: str, payload: PushRequest) -> dict[str, str]:
    # 0. Validation de la cohérence entre l'URL et le payload
    if payload.pushing_device_info.method != modal:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Incohérence au niveau du mode de connexion pour le déploiement."
        )

    profile = _resolve_profile(profile_id)
    _validate_state_against_profile(profile, payload.state)
    
    # 1. Génération des commandes CLI
    # Si current_state est fourni dans le payload, générer uniquement la diff
    current_state = getattr(payload, 'current_state', None)
    generator = GENERATORS[profile.vendor_os]
    cli_text = generator.generate(profile, payload.state, current_state)
    command_list = [line.strip() for line in cli_text.splitlines() if line.strip() and not line.startswith("!")]

    # 2. Récupération du pusher via la factory
    try:
        pusher = PusherFactory.get(modal)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 3. Envoi via Netmiko avec gestion des exceptions
    try:
        output = pusher.push_config(payload.pushing_device_info, command_list)
        return {"status": "success", "output": output}
    except (NetmikoTimeoutException, NetmikoAuthenticationException):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erreur d'authentification ou de connexion SSH")
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Échec de l'application de la configuration")