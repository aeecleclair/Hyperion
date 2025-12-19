"""File defining the functions called by the endpoints, making queries to the table using the models"""

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType
from app.core.permissions import models_permissions, schemas_permissions
from app.core.permissions.type_permissions import ModulePermissions


async def get_permissions(
    db: AsyncSession,
) -> schemas_permissions.CorePermissions:
    """Return all permissions from database"""

    result_group = (
        (await db.execute(select(models_permissions.CorePermissionGroup)))
        .scalars()
        .all()
    )
    result_account_type = (
        (await db.execute(select(models_permissions.CorePermissionAccountType)))
        .scalars()
        .all()
    )

    return schemas_permissions.CorePermissions(
        group_permissions=[
            schemas_permissions.CoreGroupPermission(
                permission_name=permission.permission_name,
                group_id=permission.group_id,
            )
            for permission in result_group
        ],
        account_type_permissions=[
            schemas_permissions.CoreAccountTypePermission(
                permission_name=permission.permission_name,
                account_type=permission.account_type,
            )
            for permission in result_account_type
        ],
    )


async def get_permissions_by_permission_name(
    db: AsyncSession,
    permission_name: ModulePermissions,
) -> schemas_permissions.CorePermissions:
    """Return permissions with name from database"""
    result_group = (
        (
            await db.execute(
                select(models_permissions.CorePermissionGroup).where(
                    models_permissions.CorePermissionGroup.permission_name
                    == permission_name,
                ),
            )
        )
        .scalars()
        .all()
    )
    result_account_type = (
        (
            await db.execute(
                select(models_permissions.CorePermissionAccountType).where(
                    models_permissions.CorePermissionAccountType.permission_name
                    == permission_name,
                ),
            )
        )
        .scalars()
        .all()
    )
    return schemas_permissions.CorePermissions(
        group_permissions=[
            schemas_permissions.CoreGroupPermission(
                permission_name=permission.permission_name,
                group_id=permission.group_id,
            )
            for permission in result_group
        ],
        account_type_permissions=[
            schemas_permissions.CoreAccountTypePermission(
                permission_name=permission.permission_name,
                account_type=permission.account_type,
            )
            for permission in result_account_type
        ],
    )


async def get_group_permission_by_group_id_and_permission_name(
    db: AsyncSession,
    permission_name: ModulePermissions,
    group_id: str,
) -> schemas_permissions.CoreGroupPermission | None:
    """Return permission with name and group id from database"""
    result = (
        (
            await db.execute(
                select(models_permissions.CorePermissionGroup).where(
                    models_permissions.CorePermissionGroup.permission_name
                    == permission_name,
                    models_permissions.CorePermissionGroup.group_id == group_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_permissions.CoreGroupPermission(
            permission_name=result.permission_name,
            group_id=result.group_id,
        )
        if result
        else None
    )


async def get_account_type_permission_by_account_type_and_permission_name(
    db: AsyncSession,
    permission_name: ModulePermissions,
    account_type: AccountType,
) -> schemas_permissions.CoreAccountTypePermission | None:
    """Return permission with name and account type from database"""
    result = (
        (
            await db.execute(
                select(models_permissions.CorePermissionAccountType).where(
                    models_permissions.CorePermissionAccountType.permission_name
                    == permission_name,
                    models_permissions.CorePermissionAccountType.account_type
                    == account_type,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_permissions.CoreAccountTypePermission(
            permission_name=result.permission_name,
            account_type=result.account_type,
        )
        if result
        else None
    )


async def create_group_permission(
    permission: schemas_permissions.CoreGroupPermission,
    db: AsyncSession,
) -> None:
    """Create a new permission in database"""
    permission_db = models_permissions.CorePermissionGroup(
        permission_name=permission.permission_name,
        group_id=permission.group_id,
    )

    db.add(permission_db)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def create_account_type_permission(
    permission: schemas_permissions.CoreAccountTypePermission,
    db: AsyncSession,
) -> None:
    """Create a new permission in database"""
    permission_db = models_permissions.CorePermissionAccountType(
        permission_name=permission.permission_name,
        account_type=permission.account_type,
    )

    db.add(permission_db)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_group_permission(
    db: AsyncSession,
    permission: schemas_permissions.CoreGroupPermission,
) -> None:
    """Delete a permission"""
    await db.execute(
        delete(models_permissions.CorePermissionGroup).where(
            models_permissions.CorePermissionGroup.permission_name
            == permission.permission_name,
            models_permissions.CorePermissionGroup.group_id == permission.group_id,
        ),
    )
    await db.commit()


async def delete_account_type_permission(
    db: AsyncSession,
    permission: schemas_permissions.CoreAccountTypePermission,
) -> None:
    """Delete a permission"""
    await db.execute(
        delete(models_permissions.CorePermissionAccountType).where(
            models_permissions.CorePermissionAccountType.permission_name
            == permission.permission_name,
            models_permissions.CorePermissionAccountType.account_type
            == permission.account_type,
        ),
    )
    await db.commit()


async def delete_permissions_by_permission_name(
    db: AsyncSession,
    permission_name: ModulePermissions,
) -> None:
    """Delete permissions from database by name"""
    await db.execute(
        delete(models_permissions.CorePermissionGroup).where(
            models_permissions.CorePermissionGroup.permission_name == permission_name,
        ),
    )
    await db.execute(
        delete(models_permissions.CorePermissionAccountType).where(
            models_permissions.CorePermissionAccountType.permission_name
            == permission_name,
        ),
    )
    await db.commit()
