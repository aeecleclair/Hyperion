from sqlite3 import IntegrityError
from typing import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_core, models_module_visibility


async def get_modules(
    db: AsyncSession,
) -> Sequence[models_module_visibility.ModuleVisibility]:
    """Return every module with their visibility"""

    result = await db.execute(
        select(
            models_module_visibility.ModuleVisibility.root,
            func.group_concat(
                models_module_visibility.ModuleVisibility.allowedGroupId, ", "
            ),
        ).group_by(models_module_visibility.ModuleVisibility.root)
    )

    return result.unique().scalars().all()


async def get_modules_by_user(
    user: models_core.CoreUser,
    db: AsyncSession,
) -> Sequence[models_module_visibility.ModuleVisibility]:
    """Return the every module with their visibility"""

    userGroupIds = map(lambda group: group.id, user.groups)

    result = await db.execute(
        select(
            models_module_visibility.ModuleVisibility.root,
            func.group_concat(
                models_module_visibility.ModuleVisibility.allowedGroupId, ", "
            ),
        )
        .where(
            models_module_visibility.ModuleVisibility.allowedGroupId._in(userGroupIds)
        )
        .group_by(models_module_visibility.ModuleVisibility.root)
    )

    return result.unique().scalars().all()


async def get_module_visibility(
    root: str,
    group_id: str,
    db: AsyncSession,
) -> models_module_visibility.ModuleVisibility:
    """Return module visibility by root and group id"""

    result = await db.execute(
        select(
            models_module_visibility.ModuleVisibility.root,
            func.group_concat(
                models_module_visibility.ModuleVisibility.allowedGroupId, ", "
            ),
        ).where(
            models_module_visibility.ModuleVisibility.root == root
            and models_module_visibility.ModuleVisibility.allowedGroupId == group_id
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
            and models_module_visibility.ModuleVisibility.allowedGroupId
            == module_visibility.allowedGroupId
        )
    )
    await db.commit()
