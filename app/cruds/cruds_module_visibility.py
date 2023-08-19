from sqlite3 import IntegrityError
from typing import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_core, models_module_visibility


async def get_modules_by_user(
    user: models_core.CoreUser,
    db: AsyncSession,
) -> Sequence[str]:
    """Return the every module with their visibility"""

    userGroupIds = list(map(lambda group: group.id, user.groups))

    result = await db.execute(
        select(models_module_visibility.ModuleVisibility.root)
        .where(
            models_module_visibility.ModuleVisibility.allowed_group_id.in_(userGroupIds)
        )
        .group_by(models_module_visibility.ModuleVisibility.root)
    )

    return result.unique().scalars().all()


async def get_allowed_groups_by_root(
    root: str,
    db: AsyncSession,
) -> Sequence[str]:
    """Return the every module with their visibility"""

    result = await db.execute(
        select(
            models_module_visibility.ModuleVisibility.allowed_group_id,
        ).where(models_module_visibility.ModuleVisibility.root == root)
    )

    resultList = result.unique().scalars().all()

    if resultList:
        return resultList
    else:
        return []


async def get_module_visibility(
    root: str,
    group_id: str,
    db: AsyncSession,
) -> models_module_visibility.ModuleVisibility | None:
    """Return module visibility by root and group id"""

    result = await db.execute(
        select(models_module_visibility.ModuleVisibility).where(
            (models_module_visibility.ModuleVisibility.allowed_group_id == group_id)
            & (models_module_visibility.ModuleVisibility.root == root)
        )
    )
    return result.unique().scalars().first()


async def create_module_visibility(
    module_visibility: models_module_visibility.ModuleVisibility,
    db: AsyncSession,
) -> models_module_visibility.ModuleVisibility:
    """Create a new module visibility in database and return it"""

    db.add(module_visibility)
    try:
        await db.commit()
        return module_visibility
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def delete_module_visibility(
    module_visibility: models_module_visibility.ModuleVisibility,
    db: AsyncSession,
):
    await db.execute(
        delete(models_module_visibility.ModuleVisibility).where(
            models_module_visibility.ModuleVisibility.root == module_visibility.root
            and models_module_visibility.ModuleVisibility.allowed_group_id
            == module_visibility.allowed_group_id
        )
    )
    await db.commit()
