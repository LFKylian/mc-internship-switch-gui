from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.cli_generators.aoscx import AosCxCliGenerator
from app.cli_generators.base import ConfigOutputGenerator
from app.domain.models import SwitchState
from app.switch_profiles.aruba_6100_48g_4sfp import ARUBA_6100_24G_4SFP, ARUBA_6100_48G_4SFP
from app.switch_profiles.base import SwitchProfile

app = FastAPI(title="Aruba Switch Configurator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # à restreindre une fois l'origine du frontend fixée
    allow_methods=["*"],
    allow_headers=["*"],
)

# GRASP Creator : seul endroit qui connaît la liste des profils disponibles.
# Ajouter un modèle de switch = ajouter une entrée ici, rien d'autre.
PROFILES: dict[str, SwitchProfile] = {
    "aruba-6100-48g-4sfp": ARUBA_6100_48G_4SFP,
    "aruba-6100-24g-4sfp": ARUBA_6100_24G_4SFP,
}

# GRASP Indirection : le contrôleur ne dépend jamais d'une classe generator
# concrète — il passe par ce registre, indexé sur profile.vendor_os.
GENERATORS: dict[str, ConfigOutputGenerator] = {
    "aoscx": AosCxCliGenerator(),
}


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
