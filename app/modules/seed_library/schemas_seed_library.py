import uuid
from datetime import date

from pydantic import BaseModel

from app.modules.seed_library.types_seed_library import (
    PlantState,
    PropagationMethod,
    SpeciesType,
)


class SpeciesBase(BaseModel):
    prefix: str  # 3 caracteres
    name: str
    difficulty: int  # entre 1 (facile) et 5 (difficile)
    species_type: SpeciesType
    card: str | None = None
    nb_seeds_recommended: int | None = None
    start_season: date | None = None
    end_season: date | None = None
    time_maturation: int | None = None  # temps en jours


# then we add an id for the Species instance to be complete
class SpeciesComplete(SpeciesBase):
    id: uuid.UUID


# we can then modify some of the variables … but not the id
class SpeciesEdit(BaseModel):
    name: str | None = None
    prefix: str | None = None  # 3 caracteres
    difficulty: int | None = None  # entre 1 (facile) et 5 (difficile)
    card: str | None = None
    species_type: SpeciesType | None = None
    nb_seeds_recommended: int | None = None
    start_season: date | None = None
    end_season: date | None = None
    time_maturation: int | None = None  # temps en jours


class PlantCreation(BaseModel):
    species_id: uuid.UUID
    propagation_method: PropagationMethod
    nb_seeds_envelope: int = 1  # 1 si propagation_method = cutting
    ancestor_id: uuid.UUID | None = None
    previous_note: str | None = None
    confidential: bool = False


class PlantSimple(BaseModel):
    id: uuid.UUID
    reference: str
    state: PlantState
    species_id: uuid.UUID
    propagation_method: PropagationMethod
    nb_seeds_envelope: int = 1  # 1 si propagation_method = cutting
    planting_date: date | None = None
    borrower_id: str | None = None
    nickname: str | None = None


class PlantComplete(PlantSimple):
    previous_note: str | None = None
    current_note: str | None = None
    borrowing_date: date | None = None
    ancestor_id: uuid.UUID | None = None
    confidential: bool = False


class PlantEdit(BaseModel):
    state: PlantState | None = None
    current_note: str | None = None
    confidential: bool = False
    planting_date: date | None = None
    borrowing_date: date | None = None
    nickname: str | None = None


class SpeciesTypesReturn(BaseModel):
    species_type: list[SpeciesType]
