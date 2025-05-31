import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ph import models_ph, schemas_ph


async def get_papers(
    db: AsyncSession,
    end_date: date | None = None,
) -> Sequence[models_ph.Paper]:
    """Return papers from the latest to the oldest"""
    result = await db.execute(
        select(models_ph.Paper)
        .where(models_ph.Paper.release_date <= (end_date or date.max))
        .order_by(models_ph.Paper.release_date.desc()),
    )
    return result.scalars().all()


async def get_paper_by_id(
    db: AsyncSession,
    paper_id: uuid.UUID,
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
    await db.flush()
    return paper


async def update_paper(
    paper_id: uuid.UUID,
    paper_update: schemas_ph.PaperUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_ph.Paper)
        .where(models_ph.Paper.id == paper_id)
        .values(**paper_update.model_dump(exclude_none=True)),
    )
    await db.flush()


async def delete_paper(
    paper_id: uuid.UUID,
    db: AsyncSession,
):
    await db.execute(
        delete(models_ph.Paper).where(models_ph.Paper.id == paper_id),
    )
    await db.flush()
