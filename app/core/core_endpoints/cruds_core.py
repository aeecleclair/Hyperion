from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.core_endpoints import models_core
from app.core.groups.groups_type import AccountType
from app.core.users import models_users


async def add_queued_email(
    email: str,
    subject: str,
    body: str,
    db: AsyncSession,
) -> None:
    email_queue = models_core.EmailQueue(
        id=UUID(),
        email=email,
        subject=subject,
        body=body,
        created_on=datetime.now(UTC),
    )
    db.add(email_queue)


async def get_queued_emails(
    db: AsyncSession,
    limit: int,
) -> Sequence[models_core.EmailQueue]:
    """
    Get a list of emails in the queue, ordered by creation date.
    This is used to send emails in the background.
    """
    result = await db.execute(
        select(models_core.EmailQueue)
        .order_by(models_core.EmailQueue.created_on)
        .limit(limit),
    )
    return result.scalars().all()


async def delete_queued_email(
    queued_email_ids: list[UUID],
    db: AsyncSession,
) -> None:
    """
    Delete emails from the queue by their IDs.
    This is used to remove emails that have been sent or are no longer needed.
    """
    await db.execute(
        delete(models_core.EmailQueue).where(
            models_core.EmailQueue.id.in_(queued_email_ids),
        ),
    )
    await db.flush()


async def get_modules_by_user(
    user: models_users.CoreUser,
    db: AsyncSession,
) -> list[str]:
    """Return the modules a user has access to"""

    result_group = list(
        (
            await db.execute(
                select(models_core.ModuleGroupVisibility.root)
                .where(
                    models_core.ModuleGroupVisibility.allowed_group_id.in_(
                        user.group_ids,
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
    await db.flush()


async def create_module_account_type_visibility(
    module_visibility: models_core.ModuleAccountTypeVisibility,
    db: AsyncSession,
) -> None:
    """Create a new module visibility in database and return it"""

    db.add(module_visibility)
    await db.flush()


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
    await db.flush()


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
    await db.flush()


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
    await db.flush()
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
    await db.flush()


async def start_isolation_mode(
    db: AsyncSession,
) -> datetime:
    """
    Set the transaction in isolation mode.
    It ensures that the transaction will not see any changes made by other transactions
    until it is committed or rolled back.
    Thus, all subsequent queries in this transaction will see the same data as at the time of the transaction start.
    """
    await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
    now = (await db.execute(select(func.now()))).scalar()
    if now is None:
        raise ValueError
    return now
