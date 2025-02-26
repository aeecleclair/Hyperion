import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.seed_library.types_seed_library import (
    PropagationMethod,
    SpeciesType,
    State,
)
from app.types import core_data


class SpeciesBase(BaseModel):
    prefix: str  # 3 caracteres
    species_name: str
    difficulty: int  # entre 1 (facile) et 5 (difficile)
    card: str
    nb_seeds_recommended: int | None = None
    species_type: SpeciesType
    start_season: datetime | None = None
    end_season: datetime | None = None
    time_maturation: int | None = None  # temps en jours

    model_config = ConfigDict(from_attributes=True)


# then we add an id for the Species instance to be complete
class SpeciesComplete(SpeciesBase):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


# we can then modify some of the variables … but not the id
class SpeciesEdit(BaseModel):
    prefix: str  # 3 caracteres
    difficulty: int  # entre 1 (facile) et 5 (difficile)
    card: str
    nb_seeds_recommended: int | None = None
    start_season: datetime | None = None
    end_season: datetime | None = None
    time_maturation: int | None = None  # temps en jours

    model_config = ConfigDict(from_attributes=True)


class PlantCreation(BaseModel):
    state: State
    species_id: uuid.UUID
    propagation_method: PropagationMethod
    nb_seeds_envelope: int = 1  # 1 si propagation_method = cutting
    ancestor_id: uuid.UUID | None = None
    previous_note: str | None = None
    current_note: str | None = None
    borrower_id: str | None = None
    confidential: bool = False
    planting_date: datetime | None = None
    borrowing_date: datetime | None = None
    nickname: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PlantSimple(BaseModel):
    id: uuid.UUID
    plant_reference: str
    state: State
    species_id: uuid.UUID
    propagation_method: PropagationMethod
    borrower_id: str | None = None
    nickname: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PlantComplete(PlantSimple):
    previous_note: str | None = None
    current_note: str | None = None
    planting_date: datetime | None = None
    borrowing_date: datetime | None = None
    ancestor_id: uuid.UUID
    nb_seeds_envelope: int = 1  # 1 si propagation_method = cutting
    confidential: bool = False

    model_config = ConfigDict(from_attributes=True)


class PlantEdit(BaseModel):
    state: State
    current_note: str | None = None
    confidential: bool = False
    planting_date: datetime | None = None
    borrowing_date: datetime | None = None
    nickname: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SeedLibraryInformation(core_data.BaseCoreData):
    facebook_url: str
    forum_url: str
    description: str  # pour expliquer le principe du module
    contact: str

    model_config = ConfigDict(from_attributes=True)
