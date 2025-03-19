import uuid
from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.seed_library.types_seed_library import (
    PlantState,
    PropagationMethod,
    SpeciesType,
)
from app.types.sqlalchemy import Base, PrimaryKey


class Species(Base):
    __tablename__ = "seed_library_species"
    id: Mapped[PrimaryKey]
    prefix: Mapped[str] = mapped_column(unique=True)  # 3 letters
    species_name: Mapped[str] = mapped_column(unique=True)
    difficulty: Mapped[int | None]
    card: Mapped[str | None]
    nb_seeds_recommended: Mapped[int | None]
    species_type: Mapped[SpeciesType | None]
    start_season: Mapped[datetime | None]
    end_season: Mapped[datetime | None]
    time_maturation: Mapped[int | None]  # number of days


class Plant(Base):
    __tablename__ = "seed_library_plants"
    id: Mapped[PrimaryKey]
    state: Mapped[PlantState] = mapped_column(index=True)
    species_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("seed_library_species.id"),
    )
    propagation_method: Mapped[PropagationMethod]
    nb_seeds_envelope: Mapped[int | None]
    plant_reference: Mapped[str] = mapped_column(unique=True)
    ancestor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("seed_library_plants.id"),
    )
    previous_note: Mapped[str | None]
    current_note: Mapped[str | None]
    borrower_id: Mapped[str | None] = mapped_column(
        ForeignKey("core_user.id"),
        index=True,
    )
    confidential: Mapped[bool | None]
    nickname: Mapped[str | None]
    planting_date: Mapped[datetime | None]
    borrowing_date: Mapped[datetime | None]
