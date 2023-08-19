from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_module_visibility
from app.dependencies import get_db, is_user_a_member, is_user_a_member_of
from app.models import models_core, models_module_visibility
from app.schemas import schemas_module_visibility
from app.utils.tools import is_group_id_valid
from app.utils.types.groups_type import GroupType
from app.utils.types.module_list import ModuleList
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/module_visibility/",
    response_model=list[schemas_module_visibility.ModuleVisibility],
    status_code=200,
    tags=[Tags.core],
)
async def get_module_visibility(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Get all existing module_visibility.

    **This endpoint is only usable by administrators**
    """

    returnModuleVisibilities = []
    for module in ModuleList:
        allowed_group_ids = await cruds_module_visibility.get_allowed_groups_by_root(
            root=module.value.root, db=db
        )
        returnModuleVisibilities.append(
            schemas_module_visibility.ModuleVisibility(
                root=module.value.root,
                allowed_group_ids=allowed_group_ids,
            )
        )

    return returnModuleVisibilities


@router.get(
    "/module_visibility/me",
    response_model=list[str],
    status_code=200,
    tags=[Tags.core],
)
async def get_user_modules_visibility(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get group user accessible root

    **This endpoint is only usable by everyone**
    """
    result = await cruds_module_visibility.get_modules_by_user(user=user, db=db)

    return result


@router.post(
    "/module_visibility/",
    response_model=schemas_module_visibility.ModuleVisibilityCreate,
    status_code=201,
    tags=[Tags.core],
)
async def add_module_visibility(
    module_visibility: schemas_module_visibility.ModuleVisibilityCreate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Add a new group to a module

    **This endpoint is only usable by administrators**
    """

    # We need to check that loaner.group_manager_id is a valid group
    if not await is_group_id_valid(module_visibility.allowed_group_id, db=db):
        raise HTTPException(
            status_code=400,
            detail="Invalid id, group_id must be a valid group id",
        )
    try:
        module_visibility_db = models_module_visibility.ModuleVisibility(
            root=module_visibility.root,
            allowed_group_id=module_visibility.allowed_group_id,
        )

        return await cruds_module_visibility.create_module_visibility(
            module_visibility=module_visibility_db, db=db
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.delete(
    "/module_visibility/{root}/{group_id}", status_code=204, tags=[Tags.core]
)
async def delete_session(
    root: str,
    group_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    await cruds_module_visibility.delete_module_visibility(
        root=root, allowed_group_id=group_id, db=db
    )
