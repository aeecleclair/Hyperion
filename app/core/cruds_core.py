from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core


async def get_all_module_visibility_membership(
    db: AsyncSession,
):
    """Return the every module with their visibility"""
    result = await db.execute(select(models_core.ModuleVisibility))
    return result.unique().scalars().all()


async def get_modules_by_user(
    user: models_core.CoreUser,
    db: AsyncSession,
) -> Sequence[str]:
    """Return the modules a user has access to"""

    userGroupIds = [group.id for group in user.groups]

    result = await db.execute(
        select(models_core.ModuleVisibility.root)
        .where(models_core.ModuleVisibility.allowed_group_id.in_(userGroupIds))
        .group_by(models_core.ModuleVisibility.root),
    )

    return result.unique().scalars().all()


async def get_allowed_groups_by_root(
    root: str,
    db: AsyncSession,
) -> Sequence[str]:
    """Return the groups allowed to access to a specific root"""

    result = await db.execute(
        select(
            models_core.ModuleVisibility.allowed_group_id,
        ).where(models_core.ModuleVisibility.root == root),
    )

    resultList = result.unique().scalars().all()

    return resultList


async def get_module_visibility(
    root: str,
    group_id: str,
    db: AsyncSession,
) -> models_core.ModuleVisibility | None:
    """Return module visibility by root and group id"""

    result = await db.execute(
        select(models_core.ModuleVisibility).where(
            models_core.ModuleVisibility.allowed_group_id == group_id,
            models_core.ModuleVisibility.root == root,
        ),
    )
    return result.unique().scalars().first()


async def create_module_visibility(
    module_visibility: models_core.ModuleVisibility,
    db: AsyncSession,
) -> models_core.ModuleVisibility:
    """Create a new module visibility in database and return it"""

    db.add(module_visibility)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    else:
        return module_visibility


async def delete_module_visibility(
    root: str,
    allowed_group_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_core.ModuleVisibility).where(
            models_core.ModuleVisibility.root == root,
            models_core.ModuleVisibility.allowed_group_id == allowed_group_id,
        ),
    )
    await db.commit()


async def get_core_data_crud(
    schema: str,
    db: AsyncSession,
) -> models_core.CoreData | None:
    """
    Get the core data model from the database.

    To manipulate core data, prefer using the `get_core_data` and `set_core_data` utils.
    """
    result = await db.execute(
        select(models_core.CoreData).where(
            models_core.CoreData.schema == schema,
        ),
    )
    return result.scalars().first()


async def add_core_data_crud(
    core_data: models_core.CoreData,
    db: AsyncSession,
) -> models_core.CoreData:
    """
    Add a core data model in database.

    To manipulate core data, prefer using the `get_core_data` and `set_core_data` utils.
    """
    db.add(core_data)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    else:
        return core_data


async def delete_core_data_crud(
    schema: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_core.CoreData).where(
            models_core.CoreData.schema == schema,
        ),
    )
    await db.commit()
