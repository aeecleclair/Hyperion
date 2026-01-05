from datetime import datetime

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.core_endpoints import models_core


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
