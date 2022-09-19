from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_campaign
from app.schemas import schemas_campaign


async def get_sections(db: AsyncSession) -> list[models_campaign.Sections]:
    """Return all users from database"""

    result = await db.execute(select(models_campaign.Sections))
    return result.scalars().all()


async def add_section(
    db: AsyncSession, section: schemas_campaign.SectionComplete
) -> None:
    db_section = models_campaign.Sections(**section.dict())
    db.add(db_section)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("This name is already used")
