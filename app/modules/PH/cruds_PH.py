from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.PH import models_PH


async def get_journals(
    db: AsyncSession,
) -> Sequence[models_PH.Journal]:
    result = await db.execute(
        select(models_PH.Journal).order_by(models_PH.Journal.release_date),
    )
    return result.scalars().all()


async def get_journal_by_id(
    db: AsyncSession,
    journal_id: str,
) -> Sequence[models_PH.Journal]:
    result = await db.execute(
        select(models_PH.Journal).where(models_PH.Journal.id == journal_id),
    )
    return result.scalars().all()


async def create_journal(
    journal: models_PH.Journal,
    db: AsyncSession,
) -> models_PH.Journal:
    """Create a new journal in database and return it"""

    db.add(journal)
    try:
        await db.commit()
        return journal
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)
