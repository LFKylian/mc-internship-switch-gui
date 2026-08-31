from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.domain.models import SwitchState


class SavedConfiguration(BaseModel):
    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=100)
    profile_id: str
    state: SwitchState
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ConfigurationRepository(ABC):
    @abstractmethod
    def save(self, config: SavedConfiguration) -> SavedConfiguration:
        ...

    @abstractmethod
    def get(self, config_id: int) -> Optional[SavedConfiguration]:
        ...

    @abstractmethod
    def list(self) -> list[SavedConfiguration]:
        ...

    @abstractmethod
    def delete(self, config_id: int) -> bool:
        ...