import logging
import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType, GroupType
from app.core.users import models_users
from app.dependencies import (
    get_db,
    is_user,
    is_user_in,
)
from app.modules.seed_library import (
    coredata_seed_library,
    cruds_seed_library,
    schemas_seed_library,
)
from app.modules.seed_library.types_seed_library import PlantState
from app.types.module import Module
from app.utils import tools
from app.utils.tools import is_user_member_of_any_group

module = Module(
    root="seed_library",
    tag="seed_library",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
)


hyperion_error_logger = logging.getLogger("hyperion.error")


@module.router.get(
    "/seed_library/species/",
    response_model=list[schemas_seed_library.SpeciesComplete],
    status_code=200,
)
async def get_all_species(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Return all species from database as a list of SpeciesComplete schemas
    """
    return await cruds_seed_library.get_all_species(db)


@module.router.get(
    "/seed_library/species/types",
    response_model=schemas_seed_library.SpeciesTypesReturn,
    status_code=200,
)
async def get_all_species_types(
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Return all available types of species from SpeciesType enum.
    """
    species_type = await cruds_seed_library.get_all_species_types()
    return schemas_seed_library.SpeciesTypesReturn(species_type=species_type)


@module.router.post(
    "/seed_library/species/",
    response_model=schemas_seed_library.SpeciesComplete,
    status_code=201,
)
async def create_species(
    species_base: schemas_seed_library.SpeciesBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.seed_library)),
):
    """
    Create a new Species by giving an SpeciesBase scheme
    **This endpoint is only usable by seed_library **
    """

    if (
        await cruds_seed_library.count_species_with_prefix(species_base.prefix, db)
    ) != 0:
        raise HTTPException(
            status_code=400,
            detail="Prefix already used",
        )

    if (await cruds_seed_library.count_species_with_name(species_base.name, db)) != 0:
        raise HTTPException(
            status_code=400,
            detail="Species name already used",
        )

    if species_base.difficulty < 1 or species_base.difficulty > 5:
        raise HTTPException(
            status_code=400,
            detail="Difficulty must be between 1 and 5",
        )

    species = schemas_seed_library.SpeciesComplete(
        id=uuid.uuid4(),
        **species_base.model_dump(),
    )

    await cruds_seed_library.create_species(species, db)
    return species


@module.router.patch(
    "/seed_library/species/{species_id}",
    status_code=204,
)
async def update_species(
    species_id: uuid.UUID,
    species_edit: schemas_seed_library.SpeciesEdit,
    user: models_users.CoreUser = Depends(is_user_in(GroupType.seed_library)),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a Specie
    **This endpoint is only usable by seed_library**
    """

    species_db = await cruds_seed_library.get_species_by_id(species_id, db)
    if species_db is None:
        raise HTTPException(404, "Species not found")

    try:
        await cruds_seed_library.update_species(
            species_id=species_id,
            species_edit=species_edit,
            db=db,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Could not update species")


@module.router.delete(
    "/seed_library/species/{species_id}",
    status_code=204,
)
async def delete_species(
    species_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.seed_library)),
):
    """
    Delete a Species
    **This endpoint is only usable by seed_library**
    """

    species = await cruds_seed_library.get_species_by_id(species_id, db)
    if species is None:
        raise HTTPException(404, "Species not found")

    active_plants = await cruds_seed_library.count_species_active_plants(species_id, db)
    if active_plants != 0:
        raise HTTPException(
            status_code=400,
            detail="Species is still in use",
        )

    return await cruds_seed_library.delete_species(
        species_id=species_id,
        db=db,
    )


@module.router.get(
    "/seed_library/plants/waiting",
    response_model=list[schemas_seed_library.PlantSimple],
    status_code=200,
)
async def get_waiting_plants(
    db: AsyncSession = Depends(get_db),
):
    """
    Return all plants where state=waiting from database as a list of PlantsComplete schemas
    """
    return await cruds_seed_library.get_waiting_plants(db)


@module.router.get(
    "/seed_library/plants/users/me",
    response_model=list[schemas_seed_library.PlantSimple],
    status_code=200,
)
async def get_my_plants(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Return all plants where user ={user_id} from database as a list of PlantsComplete schemas
    """
    return await cruds_seed_library.get_plants_by_user_id(user.id, db)


@module.router.get(
    "/seed_library/plants/users/{user_id}",
    response_model=list[schemas_seed_library.PlantSimple],
    status_code=200,
)
async def get_plants_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.seed_library)),
):
    """
    Return all plants where borrower_id = {user_id} from database as a list of PlantsComplete schemas
    """
    return await cruds_seed_library.get_plants_by_user_id(user_id, db)


@module.router.get(
    "/seed_library/plants/{plant_id}",
    response_model=schemas_seed_library.PlantComplete,
    status_code=200,
)
async def get_plant_by_id(
    plant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Return the plants where plant ={plant_id} from database as a PlantsComplete schemas
    """
    plant = await cruds_seed_library.get_plant_by_id(plant_id, db)
    if plant is None:
        raise HTTPException(404, "Plant not found")
    return plant


@module.router.post(
    "/seed_library/plants/",
    response_model=schemas_seed_library.PlantComplete,
    status_code=201,
)
async def create_plant(
    plant_base: schemas_seed_library.PlantCreation,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Create a new Plant by giving an PlantCreation scheme
    **This endpoint is only usable if the plant has an ancestor_id or by seed_library **
    """
    if plant_base.ancestor_id is None:
        if not is_user_member_of_any_group(
            user=user,
            allowed_groups=[GroupType.seed_library],
        ):
            raise HTTPException(
                status_code=403,
                detail="Please contact an Planet&co member if you are trying to donate a plant that does not come from the seed library",
            )

    species_reference = await cruds_seed_library.get_species_by_id(
        plant_base.species_id,
        db,
    )
    if species_reference is None:
        raise HTTPException(
            404,
            "Species not found",
        )
    date = datetime.now(tz=UTC)
    if species_reference:
        reference = f"{species_reference.prefix}{date.day}{date.month}{date.year}"
        plant_number = await cruds_seed_library.count_plants_created_today(
            reference,
            db,
        )
        reference = f"{species_reference.prefix}{date.day}{date.month}{date.year}{plant_number:03}"

    plant = schemas_seed_library.PlantComplete(
        id=uuid.uuid4(),
        state=PlantState.waiting,
        species_id=plant_base.species_id,
        propagation_method=plant_base.propagation_method,
        nb_seeds_envelope=plant_base.nb_seeds_envelope,
        reference=reference,
        ancestor_id=plant_base.ancestor_id,
        previous_note=plant_base.previous_note,
        current_note=None,
        borrower_id=None,
        confidential=plant_base.confidential,
        nickname=None,
        planting_date=None,
        borrowing_date=None,
    )

    await cruds_seed_library.create_plant(plant, db)
    return plant


@module.router.patch(
    "/seed_library/plants/{plant_id}",
    status_code=204,
)
async def update_plant(
    plant_id: uuid.UUID,
    plant_edit: schemas_seed_library.PlantEdit,
    user: models_users.CoreUser = Depends(is_user()),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a Plant
    **This endpoint is only usable by the owner of the plant**
    """
    plant = await cruds_seed_library.get_plant_by_id(plant_id, db)
    if plant is None:
        raise HTTPException(404, "Plant not found")

    if plant.borrower_id != user.id:
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to update plant {plant_id} since you do not own the plant",
        )
    await cruds_seed_library.update_plant(
        plant_id=plant_id,
        plant_edit=plant_edit,
        db=db,
    )


@module.router.patch(
    "/seed_library/plants/{plant_id}/admin",
    status_code=204,
)
async def update_plant_admin(
    plant_id: uuid.UUID,
    plant_edit: schemas_seed_library.PlantEdit,
    user: models_users.CoreUser = Depends(is_user_in(GroupType.seed_library)),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a Plant
    **This endpoint is only usable by seed_library**
    """
    plant = await cruds_seed_library.get_plant_by_id(plant_id, db)
    if plant is None:
        raise HTTPException(404, "Plant not found")

    await cruds_seed_library.update_plant(
        plant_id,
        plant_edit,
        db,
    )


@module.router.patch(
    "/seed_library/plants/{plant_id}/borrow",
    status_code=204,
)
async def borrow_plant(
    plant_id: uuid.UUID,
    user: models_users.CoreUser = Depends(is_user()),
    db: AsyncSession = Depends(get_db),
):
    """
    Plant borrowed by the user (modify borrowing date, borrower and state)
    """

    plant = await cruds_seed_library.get_plant_by_id(plant_id, db)
    if plant is None:
        raise HTTPException(404, "Plant not found")

    await cruds_seed_library.borrow_plant(user.id, plant_id, db)


@module.router.delete(
    "/seed_library/plants/{plant_id}",
    status_code=204,
)
async def delete_plant(
    plant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Delete a Plant
    **This endpoint is only usable by seed_library**
    """

    if not is_user_member_of_any_group(
        user=user,
        allowed_groups=[GroupType.seed_library],
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to delete plant {plant_id}",
        )

    plant = await cruds_seed_library.get_plant_by_id(plant_id, db)
    if plant is None:
        raise HTTPException(404, "Plant not found")

    if plant.state != PlantState.waiting:
        raise HTTPException(
            status_code=400,
            detail="Plant is not in waiting state",
        )

    return await cruds_seed_library.delete_plant(
        plant_id=plant_id,
        db=db,
    )


@module.router.get(
    "/seed_library/information",
    response_model=coredata_seed_library.SeedLibraryInformation,
    status_code=200,
)
async def get_seed_library_information(db: AsyncSession = Depends(get_db)):
    return await tools.get_core_data(
        coredata_seed_library.SeedLibraryInformation,
        db,
    )


@module.router.patch(
    "/seed_library/information",
    status_code=204,
)
async def update_seed_library_information(
    information: coredata_seed_library.SeedLibraryInformation,
    user: models_users.CoreUser = Depends(is_user_in(GroupType.seed_library)),
    db: AsyncSession = Depends(get_db),
):
    await tools.set_core_data(
        information,
        db,
    )
