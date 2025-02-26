import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.seed_library import (
    models_seed_library,
    schemas_seed_library,
    types_seed_library,
)

# ---------------------------------------------------------------------------- #
#                                  Species                                     #
# ---------------------------------------------------------------------------- #


async def create_species(
    species: schemas_seed_library.SpeciesComplete,
    db: AsyncSession,
) -> models_seed_library.Species:
    """Create a new Species in database and return it"""

    species_db = models_seed_library.Species(
        id=species.id,
        prefix=species.prefix,
        species_name=species.species_name,
        difficulty=species.difficulty,
        card=species.card,
        nb_seeds_recommended=species.nb_seeds_recommended,
        species_type=species.species_type,
        start_season=species.start_season,
        end_season=species.end_season,
        time_maturation=species.time_maturation,
    )
    db.add(species_db)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    return species_db


async def update_species(
    species_id: uuid.UUID,
    species_edit: schemas_seed_library.SpeciesEdit,
    db: AsyncSession,
):
    """Update a species in database"""

    await db.execute(
        update(models_seed_library.Species)
        .where(models_seed_library.Species.id == species_id)
        .values(**species_edit.model_dump(exclude_none=True)),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_species(species_id: uuid.UUID, db: AsyncSession):
    """Delete an species from database"""

    await db.execute(  # Plants from the species must be deleted first
        delete(models_seed_library.Plant).where(
            models_seed_library.Plant.species_id == species_id,
        ),
    )
    await db.execute(
        delete(models_seed_library.Species).where(
            models_seed_library.Species.id == species_id,
        ),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def get_all_species(
    db: AsyncSession,
) -> Sequence[schemas_seed_library.SpeciesComplete]:
    """Return all Species from database"""

    result = (await db.execute(select(models_seed_library.Species))).scalars().all()
    return [
        schemas_seed_library.SpeciesComplete(
            id=species.id,
            prefix=species.prefix,
            species_name=species.species_name,
            difficulty=species.difficulty,
            card=species.card,
            nb_seeds_recommended=species.nb_seeds_recommended,
            species_type=species.species_type,
            start_season=species.start_season,
            end_season=species.end_season,
            time_maturation=species.time_maturation,
        )
        for species in result
    ]


async def get_all_species_types() -> Sequence[str]:
    """Return all SpeciesType from Enum"""

    return [species_type.value for species_type in types_seed_library.SpeciesType]


async def get_species_by_id(
    species_id: uuid.UUID,
    db: AsyncSession,
) -> schemas_seed_library.SpeciesComplete | None:
    """Return species with id from database"""

    result = (
        (
            await db.execute(
                select(models_seed_library.Species).where(
                    models_seed_library.Species.id == species_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_seed_library.SpeciesComplete(
            id=result.id,
            prefix=result.prefix,
            species_name=result.species_name,
            difficulty=result.difficulty,
            card=result.card,
            nb_seeds_recommended=result.nb_seeds_recommended,
            species_type=result.species_type,
            start_season=result.start_season,
            end_season=result.end_season,
            time_maturation=result.time_maturation,
        )
        if result
        else None
    )


# ---------------------------------------------------------------------------- #
#                                  Plants                                      #
# ---------------------------------------------------------------------------- #


async def create_plant(
    plant: schemas_seed_library.PlantComplete,
    db: AsyncSession,
) -> models_seed_library.Plant:
    """Create a Plant in database"""
    plant_db = models_seed_library.Plant(
        id=plant.id,
        state=plant.state,
        species_id=plant.species_id,
        propagation_method=plant.propagation_method,
        nb_seeds_envelope=plant.nb_seeds_envelope,
        plant_reference=plant.plant_reference,
        ancestor_id=plant.ancestor_id,
        previous_note=plant.previous_note,
        current_note=plant.current_note,
        borrower_id=plant.borrower_id,
        confidential=plant.confidential,
        nickname=plant.nickname,
        planting_date=plant.planting_date,
        borrowing_date=plant.borrowing_date,
    )
    db.add(plant_db)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    return plant_db


async def update_plant(
    plant_id: uuid.UUID,
    plant_edit: schemas_seed_library.PlantEdit,
    db: AsyncSession,
):
    """Update a Plant in database"""

    await db.execute(
        update(models_seed_library.Plant)
        .where(models_seed_library.Plant.id == plant_id)
        .values(**plant_edit.model_dump(exclude_none=True)),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_plant(plant_id: uuid.UUID, db: AsyncSession):
    """Delete a Plants in database"""

    await db.execute(
        delete(models_seed_library.Plant).where(
            models_seed_library.Plant.id == plant_id,
        ),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def get_all_plants(
    db: AsyncSession,
) -> Sequence[schemas_seed_library.PlantComplete]:
    """Return all Plants from database"""

    result = (await db.execute(select(models_seed_library.Plant))).scalars().all()
    return [
        schemas_seed_library.PlantComplete(
            id=plant.id,
            state=plant.state,
            species_id=plant.species_id,
            propagation_method=plant.propagation_method,
            nb_seeds_envelope=plant.nb_seeds_envelope,
            plant_reference=plant.plant_reference,
            ancestor_id=plant.ancestor_id,
            previous_note=plant.previous_note,
            current_note=plant.current_note,
            borrower_id=plant.borrower_id,
            confidential=plant.confidential,
            nickname=plant.nickname,
            planting_date=plant.planting_date,
            borrowing_date=plant.borrowing_date,
        )
        for plant in result
    ]


async def get_plants_by_user_id(
    user_id: str,
    db: AsyncSession,
) -> Sequence[schemas_seed_library.PlantComplete]:
    """Return all Lines with user_id from database"""

    result = (
        (
            await db.execute(
                select(models_seed_library.Plant).where(
                    models_seed_library.Plant.borrower_id == user_id,
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_seed_library.PlantComplete(
            id=plant.id,
            state=plant.state,
            species_id=plant.species_id,
            propagation_method=plant.propagation_method,
            nb_seeds_envelope=plant.nb_seeds_envelope,
            plant_reference=plant.plant_reference,
            ancestor_id=plant.ancestor_id,
            previous_note=plant.previous_note,
            current_note=plant.current_note,
            borrower_id=plant.borrower_id,
            confidential=plant.confidential,
            nickname=plant.nickname,
            planting_date=plant.planting_date,
            borrowing_date=plant.borrowing_date,
        )
        for plant in result
    ]


async def get_plant_by_id(
    plant_id: uuid.UUID,
    db: AsyncSession,
) -> schemas_seed_library.PlantComplete | None:
    """Return the Plants with id from database"""

    result = (
        (
            await db.execute(
                select(models_seed_library.Plant).where(
                    models_seed_library.Plant.id == plant_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_seed_library.PlantComplete(
            id=result.id,
            state=result.state,
            species_id=result.species_id,
            propagation_method=result.propagation_method,
            nb_seeds_envelope=result.nb_seeds_envelope,
            plant_reference=result.plant_reference,
            ancestor_id=result.ancestor_id,
            previous_note=result.previous_note,
            current_note=result.current_note,
            borrower_id=result.borrower_id,
            confidential=result.confidential,
            nickname=result.nickname,
            planting_date=result.planting_date,
            borrowing_date=result.borrowing_date,
        )
        if result
        else None
    )


async def get_waiting_plants(
    db: AsyncSession,
) -> Sequence[schemas_seed_library.PlantComplete]:
    """Return all Lines with state equal waiting from database"""

    result = (
        (
            await db.execute(
                select(models_seed_library.Plant).where(
                    models_seed_library.Plant.state == types_seed_library.State.waiting,
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_seed_library.PlantComplete(
            id=plant.id,
            state=plant.state,
            species_id=plant.species_id,
            propagation_method=plant.propagation_method,
            nb_seeds_envelope=plant.nb_seeds_envelope,
            plant_reference=plant.plant_reference,
            ancestor_id=plant.ancestor_id,
            previous_note=plant.previous_note,
            current_note=plant.current_note,
            borrower_id=plant.borrower_id,
            confidential=plant.confidential,
            nickname=plant.nickname,
            planting_date=plant.planting_date,
            borrowing_date=plant.borrowing_date,
        )
        for plant in result
    ]


async def borrow_plant(
    user_id: str,
    plant_id: uuid.UUID,
    db: AsyncSession,
):
    """Borrow a Plant and mark it in database"""

    await db.execute(
        update(models_seed_library.Plant)
        .where(models_seed_library.Plant.id == plant_id)
        .values(
            borrower_id=user_id,
            borrowing_date=datetime.now(tz=UTC),
            state=types_seed_library.State.retrieved,
        ),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def count_plants_created_today(
    ref: str,
    db: AsyncSession,
) -> int:
    """Return all Lines with plant_reference beginning by ref from database"""
    result = (
        (
            await db.execute(
                select(models_seed_library.Plant).where(
                    models_seed_library.Plant.plant_reference.startswith(ref),
                ),
            )
        )
        .scalars()
        .all()
    )
    return len(result)
