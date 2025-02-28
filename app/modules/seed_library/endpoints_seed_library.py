import logging
import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.core_endpoints import models_core
from app.core.groups.groups_type import AccountType, GroupType
from app.dependencies import (
    get_db,
    is_user,
)
from app.modules.seed_library import (
    cruds_seed_library,
    schemas_seed_library,
)
from app.types.exceptions import CoreDataNotFoundError
from app.types.module import Module
from app.utils import tools
from app.utils.tools import is_user_member_of_any_group

module = Module(
    root="seed_library",
    tag="seed_library",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
)


hyperion_error_logger = logging.getLogger("hyperion.error")


# ---------------------------------------------------------------------------- #
#                                  Species                                     #
# ---------------------------------------------------------------------------- #


@module.router.get(
    "/seed_library/species/",
    response_model=list[schemas_seed_library.SpeciesComplete],
    status_code=200,
)
async def get_all_species(
    db: AsyncSession = Depends(get_db),
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
    user: models_core.CoreUser = Depends(is_user()),
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
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Create a new Species by giving an SpeciesBase scheme
    **This endpoint is only usable by seed_library **
    """

    if not is_user_member_of_any_group(
        user=user,
        allowed_groups=[GroupType.seed_library],
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to create a species",
        )

    existing_species = await cruds_seed_library.get_all_species(db)
    for species in existing_species:
        if species.prefix == species_base.prefix:
            raise HTTPException(400, "Prefix already used.")

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
    user: models_core.CoreUser = Depends(is_user()),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a Specie
    **This endpoint is only usable by seed_library**
    """
    if not (
        is_user_member_of_any_group(
            user=user,
            allowed_groups=[GroupType.seed_library],
        )
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to update species {species_id}",
        )

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
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Delete a Species
    **This endpoint is only usable by seed_library**
    """

    if not is_user_member_of_any_group(
        user=user,
        allowed_groups=[GroupType.seed_library],
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to delete species {species_id}",
        )

    species = await cruds_seed_library.get_species_by_id(species_id, db)
    if species is None:
        raise HTTPException(404, "Species does not exist.")

    return await cruds_seed_library.delete_species(
        species_id=species_id,
        db=db,
    )


# ---------------------------------------------------------------------------- #
#                                  Plants                                      #
# ---------------------------------------------------------------------------- #


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
    "/seed_library/plants/users/{user_id}",
    response_model=list[schemas_seed_library.PlantSimple],
    status_code=200,
)
async def get_plants_by_user_id(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Return all plants where borrower_id = {user_id} from database as a list of PlantsComplete schemas
    """

    if not (
        is_user_member_of_any_group(
            user=user,
            allowed_groups=[GroupType.seed_library],
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to see plants from this user",
        )
    return await cruds_seed_library.get_plants_by_user_id(user_id, db)


@module.router.get(
    "/seed_library/plants/users/me",
    response_model=list[schemas_seed_library.PlantSimple],
    status_code=200,
)
async def get_my_plants(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Return all plants where user ={user_id} from database as a list of PlantsComplete schemas
    """
    return await cruds_seed_library.get_plants_by_user_id(user.id, db)


@module.router.get(
    "/seed_library/plants/{plant_id}",
    response_model=schemas_seed_library.PlantSimple,
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
        raise HTTPException(404, "Plant does not exist.")
    return plant


@module.router.post(
    "/seed_library/plants/",
    response_model=schemas_seed_library.PlantComplete,
    status_code=201,
)
async def create_plant(
    plant_base: schemas_seed_library.PlantCreation,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
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
        plant_reference = (
            str(species_reference.prefix)
            + str(date.day)
            + str(date.month)
            + str(date.year)
        )
        plant_number = await cruds_seed_library.count_plants_created_today(
            plant_reference,
            db,
        )

        plant_reference = (
            plant_reference + "0" * (3 - len(str(plant_number))) + str(plant_number)
        )

    plant = schemas_seed_library.PlantComplete(
        id=uuid.uuid4(),
        state=plant_base.state,
        species_id=plant_base.species_id,
        propagation_method=plant_base.propagation_method,
        nb_seeds_envelope=plant_base.nb_seeds_envelope,
        plant_reference=plant_reference,
        ancestor_id=plant_base.ancestor_id,
        previous_note=plant_base.previous_note,
        current_note=plant_base.current_note,
        borrower_id=plant_base.borrower_id,
        confidential=plant_base.confidential,
        nickname=plant_base.nickname,
        planting_date=plant_base.planting_date,
        borrowing_date=plant_base.borrowing_date,
    )

    await cruds_seed_library.create_plant(plant, db)
    return plant


@module.router.patch(
    "/seed_library/plant/{plant_id}",
    status_code=204,
)
async def update_plant(
    plant_id: uuid.UUID,
    plant_edit: schemas_seed_library.PlantEdit,
    user: models_core.CoreUser = Depends(is_user()),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a Plant
    **This endpoint is only usable by the owner of the plant**
    """
    plant = await cruds_seed_library.get_plant_by_id(plant_id, db)
    if plant is None:
        raise HTTPException(404, "Plant does not exist.")

    if plant.borrower_id != user.id:
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to update plant {plant_id} since you do not own the plant",
        )
    try:
        await cruds_seed_library.update_plant(
            plant_id=plant_id,
            plant_edit=plant_edit,
            db=db,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@module.router.patch(
    "/seed_library/plant/{plant_id}/admin",
    status_code=204,
)
async def update_plant_admin(
    plant_id: uuid.UUID,
    plant_edit: schemas_seed_library.PlantEdit,
    user: models_core.CoreUser = Depends(is_user()),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a Plant
    **This endpoint is only usable by seed_library**
    """
    if not (
        is_user_member_of_any_group(
            user=user,
            allowed_groups=[GroupType.seed_library],
        )
    ):
        raise HTTPException(
            status_code=403,
            detail=f"You are not allowed to update plant {plant_id}",
        )

    try:
        await cruds_seed_library.update_plant(
            plant_id,
            plant_edit,
            db,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@module.router.patch(
    "/seed_library/plants/{plant_id}/borrow",
    status_code=204,
)
async def borrow_plant(
    plant_id: uuid.UUID,
    user: models_core.CoreUser = Depends(is_user()),
    db: AsyncSession = Depends(get_db),
):
    """
    Plant borrowed by the user (modify borrowing date, borrower and state)
    """

    try:
        await cruds_seed_library.borrow_plant(user.id, plant_id, db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@module.router.delete(
    "/seed_library/plants/{plant_id}",
    status_code=204,
)
async def delete_plant(
    plant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
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
        raise HTTPException(404, "Plant does not exist.")

    return await cruds_seed_library.delete_plant(
        plant_id=plant_id,
        db=db,
    )


# ---------------------------------------------------------------------------- #
#                              SeedLibraryInformation                          #
# ---------------------------------------------------------------------------- #


@module.router.get(
    "/seed_library/seed_library_information/",
    response_model=schemas_seed_library.SeedLibraryInformation,
    status_code=200,
)
async def get_seed_library_information(db: AsyncSession = Depends(get_db)):
    try:
        info = await tools.get_core_data(
            schemas_seed_library.SeedLibraryInformation,
            db,
        )
    except CoreDataNotFoundError:
        await tools.set_core_data(
            schemas_seed_library.SeedLibraryInformation(
                facebook_url="",
                forum_url="",
                description="",
                contact="",
            ),
            db,
        )
        return await tools.get_core_data(
            schemas_seed_library.SeedLibraryInformation,
            db,
        )
    return info


@module.router.patch(
    "/seed_library/seed_library_information",
    status_code=204,
)
async def update_seed_library_information(
    facebook_url: str,
    forum_url: str,
    description: str,
    contact: str,
    user: models_core.CoreUser = Depends(is_user()),
    db: AsyncSession = Depends(get_db),
):
    if not (
        is_user_member_of_any_group(
            user=user,
            allowed_groups=[GroupType.seed_library],
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to update seed_library_information",
        )
    await tools.set_core_data(
        schemas_seed_library.SeedLibraryInformation(
            facebook_url=facebook_url,
            forum_url=forum_url,
            description=description,
            contact=contact,
        ),
        db,
    )
