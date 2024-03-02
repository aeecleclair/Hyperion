from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core


async def get_visible_roots_by_user(
    user: models_core.CoreUser,
    db: AsyncSession,
) -> Sequence[str]:
    """
    Return every visible roots a user groups' allow him to access
    """

    user_group_ids = [group.id for group in user.groups]

    result = await db.execute(
        select(models_core.ModuleVisibility.root)
        .where(
            models_core.ModuleVisibility.allowed_group_id.in_(user_group_ids),
            models_core.ModuleVisibility.visible,
        )
        .group_by(models_core.ModuleVisibility.root)
    )

    return result.unique().scalars().all()


async def get_allowed_groups_ids_by_root(
    root: str,
    db: AsyncSession,
) -> Sequence[str]:
    """
    Return group ids that can access a given root
    """

    result = await db.execute(
        select(
            models_core.ModuleVisibility.allowed_group_id,
        ).where(
            models_core.ModuleVisibility.root == root,
            models_core.ModuleVisibility.visible,
        )
    )

    return result.unique().scalars().all()


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


async def disable_module_visibility(
    root: str,
    allowed_group_id: str,
    db: AsyncSession,
):
    await db.execute(
        update(models_core.ModuleVisibility)
        .where(
            models_core.ModuleVisibility.root == root,
            models_core.ModuleVisibility.allowed_group_id == allowed_group_id,
        )
        .values(visible=False)
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
        return core_data
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


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
