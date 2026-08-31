from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.cli_generators.aoscx import AosCxCliGenerator
from app.cli_generators.base import ConfigOutputGenerator
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


def get_config_repo(db: Session = Depends(get_db)) -> ConfigurationRepository:
    return PostgresConfigurationRepository(db)


@app.get("/api/profiles")
def list_profiles() -> dict[str, str]:
    return {key: profile.model for key, profile in PROFILES.items()}


@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: str) -> SwitchProfile:
    profile = PROFILES.get(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profil inconnu")
    return profile


@app.post("/api/profiles/{profile_id}/generate-cli")
def generate_cli(profile_id: str, state: SwitchState) -> dict[str, str]:
    profile = PROFILES.get(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profil inconnu")

    unknown_ports = set(state.ports) - profile.port_ids()
    if unknown_ports:
        raise HTTPException(
            status_code=422,
            detail=f"Ports inconnus pour ce profil : {sorted(unknown_ports)}",
        )

    generator = GENERATORS[profile.vendor_os]
    return {"cli": generator.generate(profile, state)}


# --- API Saved Configurations ---

@app.post("/api/configurations", response_model=SavedConfiguration, status_code=status.HTTP_201_CREATED)
def save_configuration(
    config: SavedConfiguration,
    repo: ConfigurationRepository = Depends(get_config_repo),
):
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