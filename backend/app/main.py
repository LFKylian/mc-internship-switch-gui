from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from netmiko import NetmikoTimeoutException, NetmikoAuthenticationException
from sqlalchemy.orm import Session

from app.cli_generators.aoscx import AosCxCliGenerator
from app.cli_generators.base import ConfigOutputGenerator
from app.config_pushers.factory import PusherFactory
from app.config_getters.factory import GetterFactory
from app.config_getters.ssh import AosCxSSHConfigGetter
from app.domain.push import PushRequest
from app.domain.get import GetRequest, GetResponse
from app.database import get_db
from app.domain.configurations import ConfigurationRepository, SavedConfiguration
from app.domain.models import SwitchState
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

# Initialisation des getters disponibles
GetterFactory.register("ssh", AosCxSSHConfigGetter)


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
def generate_cli(profile_id: str, state: SwitchState) -> dict[str, str]:
    profile = _resolve_profile(profile_id)
    _validate_state_against_profile(profile, state)
    generator = GENERATORS[profile.vendor_os]
    return {"cli": generator.generate(profile, state)}


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
    generator = GENERATORS[profile.vendor_os]
    cli_text = generator.generate(profile, payload.state)
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


# --- API Get Configurations ---

@app.post("/api/get-configuration/{modal}", response_model=GetResponse, status_code=status.HTTP_200_OK)
def get_configuration(modal: str, payload: GetRequest) -> GetResponse:
    """
    Récupère la configuration depuis un switch via SSH et la parse.
    Implémente le principe GRASP : Controller (coordonne les opérations).
    """
    # 0. Validation de la cohérence entre l'URL et le payload
    if payload.getting_device_info.method != modal:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Incohérence au niveau du mode de connexion pour la récupération."
        )

    # 1. Vérification que le getter est disponible
    try:
        getter = GetterFactory.get(modal)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 2. Vérification que le getter peut gérer cette requête
    if not getter.can_get(payload.getting_device_info):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La méthode '{modal}' ne peut pas récupérer la configuration pour ce type de switch"
        )

    # 3. Récupération et parsing de la configuration
    try:
        state = getter.get_config(payload.getting_device_info)
        return GetResponse(status="success", state=state.model_dump())
    except (NetmikoTimeoutException, NetmikoAuthenticationException):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erreur d'authentification ou de connexion SSH")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Échec de la récupération de la configuration: {str(e)}"
        )