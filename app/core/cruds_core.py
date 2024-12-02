from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import AccountType


async def get_modules_by_user(
    user: models_core.CoreUser,
    db: AsyncSession,
) -> list[str]:
    """Return the modules a user has access to"""

    userGroupIds = [group.id for group in user.groups]

    result_group = list(
        (
            await db.execute(
                select(models_core.ModuleGroupVisibility.root)
                .where(
                    models_core.ModuleGroupVisibility.allowed_group_id.in_(
                        userGroupIds,
                    ),
                )
                .group_by(models_core.ModuleGroupVisibility.root),
            )
        )
        .unique()
        .scalars()
        .all(),
    )
    result_account_type = list(
        (
            await db.execute(
                select(models_core.ModuleAccountTypeVisibility.root).where(
                    models_core.ModuleAccountTypeVisibility.allowed_account_type
                    == user.account_type,
                ),
            )
        )
        .unique()
        .scalars()
        .all(),
    )

    return result_group + result_account_type


async def get_allowed_groups_by_root(
    root: str,
    db: AsyncSession,
) -> Sequence[str]:
    """Return the groups allowed to access to a specific root"""

    result = await db.execute(
        select(
            models_core.ModuleGroupVisibility.allowed_group_id,
        ).where(models_core.ModuleGroupVisibility.root == root),
    )

    return result.unique().scalars().all()


async def get_allowed_account_types_by_root(
    root: str,
    db: AsyncSession,
) -> Sequence[str]:
    """Return the groups allowed to access to a specific root"""

    result = await db.execute(
        select(
            models_core.ModuleAccountTypeVisibility.allowed_account_type,
        ).where(models_core.ModuleAccountTypeVisibility.root == root),
    )

    return result.unique().scalars().all()


async def create_module_group_visibility(
    module_visibility: models_core.ModuleGroupVisibility,
    db: AsyncSession,
) -> None:
    """Create a new module visibility in database and return it"""

    db.add(module_visibility)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def create_module_account_type_visibility(
    module_visibility: models_core.ModuleAccountTypeVisibility,
    db: AsyncSession,
) -> None:
    """Create a new module visibility in database and return it"""

    db.add(module_visibility)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def delete_module_group_visibility(
    root: str,
    allowed_group_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_core.ModuleGroupVisibility).where(
            models_core.ModuleGroupVisibility.root == root,
            models_core.ModuleGroupVisibility.allowed_group_id == allowed_group_id,
        ),
    )
    await db.commit()


async def delete_module_account_type_visibility(
    root: str,
    allowed_account_type: AccountType,
    db: AsyncSession,
):
    await db.execute(
        delete(models_core.ModuleAccountTypeVisibility).where(
            models_core.ModuleAccountTypeVisibility.root == root,
            models_core.ModuleAccountTypeVisibility.allowed_account_type
            == allowed_account_type,
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
