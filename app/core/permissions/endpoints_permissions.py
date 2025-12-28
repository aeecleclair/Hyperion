"""
File defining the API itself, using fastAPI and schemas, and calling the cruds functions

Group management is part of the core of Hyperion. These endpoints allow managing membership between users and groups.
"""

import logging
from typing import TYPE_CHECKING, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import GroupType
from app.core.permissions import cruds_permissions, schemas_permissions
from app.dependencies import (
    get_db,
    is_user,
    is_user_in,
)
from app.types.module import CoreModule
from app.utils.tools import is_group_id_valid

if TYPE_CHECKING:
    from app.core.permissions.type_permissions import ModulePermissions

router = APIRouter(tags=["Permissions"])

core_module = CoreModule(
    root="permissions",
    tag="Permissions",
    router=router,
    factory=None,
)

hyperion_security_logger = logging.getLogger("hyperion.security")


@router.get(
    "/permissions/list",
    response_model=list[str],
    status_code=200,
)
async def read_permissions_list(
    user=Depends(is_user()),
):
    """
    Return all permissions from database
    """
    from app.module import full_name_permissions_list

    return full_name_permissions_list


@router.get(
    "/permissions/",
    response_model=list[schemas_permissions.CorePermissions],
    status_code=200,
)
async def read_permissions(
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user()),
):
    """
    Return all permissions from database
    """
    from app.module import permissions_list

    return await cruds_permissions.get_permissions(permissions_list, db)


@router.get(
    "/permissions/{permission_name}",
    response_model=schemas_permissions.CorePermissions,
    status_code=200,
)
async def read_permission(
    permission_name: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
):
    """
    Return permission with name from database
    """
    from app.module import permissions_list

    if permission_name not in permissions_list:
        raise HTTPException(
            status_code=404,
            detail="Permission not found",
        )
    permission = cast(
        "ModulePermissions",
        permission_name,
    )

    return await cruds_permissions.get_permissions_by_permission_name(
        db,
        permission,
    )


@router.post(
    "/permissions/",
    status_code=201,
)
async def create_permission(
    permission: schemas_permissions.CoreGroupPermission
    | schemas_permissions.CoreAccountTypePermission,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
):
    """
    Create a new permission in database
    """
    from app.module import permissions_list

    if permission.permission_name not in permissions_list:
        raise HTTPException(
            status_code=404,
            detail="Permission not found",
        )
    if isinstance(permission, schemas_permissions.CoreGroupPermission):
        if not await is_group_id_valid(permission.group_id, db):
            raise HTTPException(
                status_code=404,
                detail="Group not found",
            )
        await cruds_permissions.create_group_permission(permission, db)
    else:
        await cruds_permissions.create_account_type_permission(permission, db)
    return {"message": "Permission created successfully"}


@router.delete(
    "/permissions/",
    status_code=204,
)
async def delete_permission(
    permission: schemas_permissions.CoreGroupPermission
    | schemas_permissions.CoreAccountTypePermission,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
):
    """
    Delete a permission from database by name
    """
    from app.module import permissions_list

    if permission.permission_name not in permissions_list:
        raise HTTPException(
            status_code=404,
            detail="Permission not found",
        )
    permission_name = cast(
        "ModulePermissions",
        permission.permission_name,
    )
    if isinstance(permission, schemas_permissions.CoreGroupPermission):
        if not await is_group_id_valid(permission.group_id, db):
            raise HTTPException(
                status_code=404,
                detail="Group not found",
            )
        group_permission_db = await cruds_permissions.get_group_permission_by_group_id_and_permission_name(
            db,
            permission_name,
            permission.group_id,
        )
        if not group_permission_db:
            raise HTTPException(
                status_code=404,
                detail="Permission not found",
            )
        await cruds_permissions.delete_group_permission(db, permission)
    else:
        account_type_permission_db = await cruds_permissions.get_account_type_permission_by_account_type_and_permission_name(
            db,
            permission_name,
            permission.account_type,
        )
        if not account_type_permission_db:
            raise HTTPException(
                status_code=404,
                detail="Permission not found",
            )
        await cruds_permissions.delete_account_type_permission(db, permission)
    return {"message": "Permission deleted successfully"}
