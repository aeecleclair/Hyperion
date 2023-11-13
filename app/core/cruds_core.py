from typing import Sequence

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

    userGroupIds = list(map(lambda group: group.id, user.groups))

    result = await db.execute(
        select(models_core.ModuleVisibility.root)
        .where(models_core.ModuleVisibility.allowed_group_id.in_(userGroupIds))
        .group_by(models_core.ModuleVisibility.root)
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
        ).where(models_core.ModuleVisibility.root == root)
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
        )
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
        return module_visibility
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def delete_module_visibility(
    root: str,
    allowed_group_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_core.ModuleVisibility).where(
            models_core.ModuleVisibility.root == root,
            models_core.ModuleVisibility.allowed_group_id == allowed_group_id,
        )
    )
    await db.commit()
