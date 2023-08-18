from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.types.module import Module
from app.cruds import cruds_module_visibility
from app.dependencies import get_db, is_user_a_member_of
from app.models import models_core
from app.schemas import schemas_module_visibility
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

module_visibility = Module(root="/module_visibility")


@module_visibility.router.get(
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
    result = await cruds_module_visibility.get_modules(db=db)
    returnModuleVisibilities = []
    for module in result:
        if module.allowedGroupId != "":
            returnModuleVisibilities.append(
                schemas_module_visibility.ModuleVisibility(
                    root=module.root, allowedGroupIds=module.allowedGroupId.split(", ")
                )
            )
        else:
            returnModuleVisibilities.append(
                schemas_module_visibility.ModuleVisibility(
                    root=module.root, allowedGroupIds=[]
                )
            )
    return returnModuleVisibilities


@module_visibility.router.get(
    "/module_visibility/me",
    response_model=list[schemas_module_visibility.ModuleVisibility],
    status_code=200,
    tags=[Tags.core],
)
async def get_user_modules_visibility(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Get group user module visibility.

    **This endpoint is only usable by everyone**
    """
    result = await cruds_module_visibility.get_modules_by_user(user=user, db=db)
    returnModuleVisibilities = []
    for module in result:
        if module.allowedGroupId != "":
            returnModuleVisibilities.append(
                schemas_module_visibility.ModuleVisibility(
                    root=module.root, allowedGroupIds=module.allowedGroupId.split(", ")
                )
            )
        else:
            returnModuleVisibilities.append(
                schemas_module_visibility.ModuleVisibility(
                    root=module.root, allowedGroupIds=[]
                )
            )
    return returnModuleVisibilities
