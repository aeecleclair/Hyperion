import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.associations import (
    cruds_associations,
    models_associations,
    schemas_associations,
)
from app.core.associations.factory_associations import AssociationsFactory
from app.core.groups.groups_type import GroupType
from app.core.users import models_users
from app.dependencies import (
    get_db,
    is_user,
    is_user_in,
)
from app.types.content_type import ContentType
from app.types.module import CoreModule
from app.utils.tools import get_file_from_data, save_file_as_data

router = APIRouter(tags=["Associations"])

core_module = CoreModule(
    root="associations",
    tag="Associations",
    router=router,
    factory=AssociationsFactory(),
)


@router.get(
    "/associations/",
    response_model=list[schemas_associations.Association],
    status_code=200,
)
async def read_associations(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Return all associations

    **User must be authenticated**
    """

    return await cruds_associations.get_associations(db=db)


@router.get(
    "/associations/me",
    response_model=list[schemas_associations.Association],
    status_code=200,
)
async def read_associations_me(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Return all associations the current user has the right to manage

    **User must be authenticated**
    """

    return await cruds_associations.get_associations_for_groups(
        group_ids=user.group_ids,
        db=db,
    )


@router.post(
    "/associations/",
    response_model=schemas_associations.Association,
    status_code=201,
)
async def create_association(
    association: schemas_associations.AssociationBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Create a new association

    **This endpoint is only usable by administrators**
    """
    if (
        await cruds_associations.get_association_by_name(name=association.name, db=db)
        is not None
    ):
        raise HTTPException(
            status_code=400,
            detail="A association with this name already exist",
        )

    db_association = models_associations.CoreAssociation(
        id=uuid.uuid4(),
        name=association.name,
        group_id=association.group_id,
    )
    await cruds_associations.create_association(
        association=db_association,
        db=db,
    )

    return db_association


@router.patch(
    "/associations/{association_id}",
    status_code=204,
)
async def update_association(
    association_id: uuid.UUID,
    association_update: schemas_associations.AssociationUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
):
    """
    Update the name or the description of a association.

    **This endpoint is only usable by administrators**
    """
    association = await cruds_associations.get_association_by_id(
        association_id=association_id,
        db=db,
    )
    if not association:
        raise HTTPException(status_code=404, detail="Association not found")

    # If the request ask to update the association name, we need to check it is available
    if association_update.name and association_update.name != association.name:
        if (
            await cruds_associations.get_association_by_name(
                name=association_update.name,
                db=db,
            )
            is not None
        ):
            raise HTTPException(
                status_code=400,
                detail="A association with the name already exist",
            )

    await cruds_associations.update_association(
        db=db,
        association_id=association_id,
        association_update=association_update,
    )


@router.post(
    "/associations/{association_id}/logo",
    status_code=204,
)
async def create_association_logo(
    association_id: uuid.UUID,
    image: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Upload a logo for an association

    **This endpoint is only usable by administrators**
    """

    association = await cruds_associations.get_association_by_id(
        db=db,
        association_id=association_id,
    )
    if not association:
        raise HTTPException(status_code=404, detail="Association not found")

    await save_file_as_data(
        upload_file=image,
        directory="associations/logos",
        filename=association_id,
        max_file_size=4 * 1024 * 1024,
        accepted_content_types=[
            ContentType.jpg,
            ContentType.png,
            ContentType.webp,
        ],
    )


@router.get(
    "/associations/{association_id}/logo",
    response_class=FileResponse,
    status_code=200,
)
async def read_association_logo(
    association_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Get the logo of an association

    **User must be authenticated**
    """

    association = await cruds_associations.get_association_by_id(
        db=db,
        association_id=association_id,
    )
    if not association:
        raise HTTPException(status_code=404, detail="Association not found")

    return get_file_from_data(
        directory="associations/logos",
        filename=association_id,
        raise_http_exception=True,
    )
