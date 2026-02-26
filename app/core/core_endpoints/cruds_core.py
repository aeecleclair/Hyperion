import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.core_endpoints import models_core


async def add_queued_email(
    email: str,
    subject: str,
    body: str,
    db: AsyncSession,
) -> None:
    email_queue = models_core.EmailQueue(
        id=uuid.uuid4(),
        email=email,
        subject=subject,
        body=body,
        created_on=datetime.now(UTC),
    )
    db.add(email_queue)
    await db.flush()


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
