from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.database import Base
from app.domain.configurations import ConfigurationRepository, SavedConfiguration
from app.domain.models import SwitchState


class ConfigurationORM(Base):
    __tablename__ = "configurations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    profile_id = Column(String(50), nullable=False)
    state = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class PostgresConfigurationRepository(ConfigurationRepository):
    def __init__(self, db_session: Session):
        self.db = db_session

    def save(self, config: SavedConfiguration) -> SavedConfiguration:
        if config.id:
            orm_obj = self.db.query(ConfigurationORM).filter(ConfigurationORM.id == config.id).first()
            if orm_obj:
                orm_obj.name = config.name
                orm_obj.profile_id = config.profile_id
                orm_obj.state = config.state.model_dump()
                orm_obj.updated_at = datetime.now(timezone.utc)
                self.db.commit()
                self.db.refresh(orm_obj)
                return self._to_domain(orm_obj)

        orm_obj = ConfigurationORM(
            name=config.name,
            profile_id=config.profile_id,
            state=config.state.model_dump(),
        )
        self.db.add(orm_obj)
        self.db.commit()
        self.db.refresh(orm_obj)
        return self._to_domain(orm_obj)

    def get(self, config_id: int) -> Optional[SavedConfiguration]:
        orm_obj = self.db.query(ConfigurationORM).filter(ConfigurationORM.id == config_id).first()
        return self._to_domain(orm_obj) if orm_obj else None

    def list(self) -> list[SavedConfiguration]:
        records = self.db.query(ConfigurationORM).order_by(ConfigurationORM.updated_at.desc()).all()
        return [self._to_domain(r) for r in records]

    def delete(self, config_id: int) -> bool:
        orm_obj = self.db.query(ConfigurationORM).filter(ConfigurationORM.id == config_id).first()
        if not orm_obj:
            return False
        self.db.delete(orm_obj)
        self.db.commit()
        return True

    @staticmethod
    def _to_domain(orm: ConfigurationORM) -> SavedConfiguration:
        return SavedConfiguration(
            id=orm.id,
            name=orm.name,
            profile_id=orm.profile_id,
            state=SwitchState.model_validate(orm.state),
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )