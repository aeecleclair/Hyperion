"""
File defining the API itself, using fastAPI and schemas, and calling the cruds functions

Group management is part of the core of Hyperion. These endpoints allow managing membership between users and groups.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import GroupType
from app.core.permissions import cruds_permissions, schemas_permissions
from app.dependencies import (
    get_db,
    is_user_in,
)
from app.module import full_name_permissions_list, permissions_list
from app.types.module import CoreModule
from app.utils.tools import is_group_id_valid

router = APIRouter(tags=["Groups"])

core_module = CoreModule(
    root="permissions",
    tag="Permissions",
    router=router,
)

hyperion_security_logger = logging.getLogger("hyperion.security")


@router.get(
    "/permissions/list",
    response_model=list[str],
    status_code=200,
)
async def read_permissions_list(
    user=Depends(is_user_in(GroupType.admin)),
):
    """
    Return all permissions from database
    """

    return full_name_permissions_list


@router.get(
    "/permissions/",
    response_model=list[schemas_permissions.CorePermission],
    status_code=200,
)
async def read_permissions(
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
):
    """
    Return all permissions from database
    """

    return await cruds_permissions.get_permissions(db)


@router.get(
    "/permissions/{permission_name}",
    response_model=list[schemas_permissions.CorePermission],
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
    if permission_name not in permissions_list:
        raise HTTPException(
            status_code=404,
            detail="Permission not found",
        )

    return await cruds_permissions.get_permissions_by_permission_name(
        db,
        permission_name,
    )


@router.post(
    "/permissions/",
    status_code=201,
)
async def create_permission(
    permission: schemas_permissions.CorePermission,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
):
    """
    Create a new permission in database
    """
    if not await is_group_id_valid(permission.group_id, db):
        raise HTTPException(
            status_code=404,
            detail="Group not found",
        )
    if permission.permission_name not in permissions_list:
        raise HTTPException(
            status_code=404,
            detail="Permission not found",
        )

    await cruds_permissions.create_permission(permission, db)
    return {"message": "Permission created successfully"}


@router.delete(
    "/permissions/",
    status_code=204,
)
async def delete_permission(
    permission: schemas_permissions.CorePermission,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
):
    """
    Delete a permission from database by name
    """
    permission_db = (
        await cruds_permissions.get_permissions_by_group_id_and_permission_name(
            db,
            permission.permission_name,
            permission.group_id,
        )
    )
    if not permission_db:
        raise HTTPException(
            status_code=404,
            detail="Permission not found",
        )

    await cruds_permissions.delete_permission(db, permission)
    return {"message": "Permission deleted successfully"}
