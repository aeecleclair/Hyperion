from typing import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ph import models_ph


async def get_papers(
    db: AsyncSession,
) -> Sequence[models_ph.Paper]:
    result = await db.execute(
        select(models_ph.Paper).order_by(models_ph.Paper.release_date),
    )
    return result.scalars().all()


async def get_paper_by_id(
    db: AsyncSession,
    paper_id: str,
) -> Sequence[models_ph.Paper]:
    result = await db.execute(
        select(models_ph.Paper).where(models_ph.Paper.id == paper_id),
    )
    return result.scalars().all()


async def create_paper(
    paper: models_ph.Paper,
    db: AsyncSession,
) -> models_ph.Paper:
    """Create a new paper in database and return it"""

    db.add(paper)
    try:
        await db.commit()
        return paper
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)
