"""File defining the functions called by the endpoints, making queries to the table using the models"""

from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import models_permissions, schemas_permissions
from app.core.permissions.type_permissions import ModulePermissions


async def get_permissions(
    db: AsyncSession,
) -> Sequence[schemas_permissions.CorePermission]:
    """Return all permissions from database"""

    result = (
        (await db.execute(select(models_permissions.CorePermission))).scalars().all()
    )
    return [
        schemas_permissions.CorePermission(
            permission_name=permission.permission_name,
            group_id=permission.group_id,
        )
        for permission in result
    ]


async def get_permissions_by_group_id_and_permission_name(
    db: AsyncSession,
    permission_name: ModulePermissions | str,
    group_id: str,
) -> schemas_permissions.CorePermission | None:
    """Return permission with name from database"""
    result = (
        (
            await db.execute(
                select(models_permissions.CorePermission).where(
                    models_permissions.CorePermission.permission_name
                    == permission_name,
                    models_permissions.CorePermission.group_id == group_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_permissions.CorePermission(
            permission_name=result.permission_name,
            group_id=result.group_id,
        )
        if result
        else None
    )


async def get_permissions_by_permission_name(
    db: AsyncSession,
    permission_name: ModulePermissions | str,
) -> Sequence[schemas_permissions.CorePermission]:
    """Return permission with name from database"""
    result = (
        (
            await db.execute(
                select(models_permissions.CorePermission).where(
                    models_permissions.CorePermission.permission_name
                    == permission_name,
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_permissions.CorePermission(
            permission_name=permission.permission_name,
            group_id=permission.group_id,
        )
        for permission in result
    ]


async def create_permission(
    permission: schemas_permissions.CorePermission,
    db: AsyncSession,
) -> None:
    """Create a new permission in database and return it"""
    permission_db = models_permissions.CorePermission(
        permission_name=permission.permission_name,
        group_id=permission.group_id,
    )

    db.add(permission_db)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_permission(
    db: AsyncSession,
    permission: schemas_permissions.CorePermission,
) -> None:
    """Delete a permission from database by name"""
    await db.execute(
        delete(models_permissions.CorePermission).where(
            models_permissions.CorePermission.permission_name
            == permission.permission_name,
            models_permissions.CorePermission.group_id == permission.group_id,
        ),
    )
    await db.commit()


async def delete_permissions_by_permission_name(
    db: AsyncSession,
    permission_name: ModulePermissions,
) -> None:
    """Delete a permission from database by name"""
    await db.execute(
        delete(models_permissions.CorePermission).where(
            models_permissions.CorePermission.permission_name == permission_name,
        ),
    )
    await db.commit()


async def delete_unused_permissions(
    db: AsyncSession,
    used_permissions: Sequence[ModulePermissions],
) -> None:
    """Delete all permissions that are not used anymore"""
    await db.execute(
        delete(models_permissions.CorePermission).where(
            models_permissions.CorePermission.permission_name.notin_(used_permissions),
        ),
    )
    await db.commit()
