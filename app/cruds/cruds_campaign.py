from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import models_campaign
from app.schemas import schemas_campaign


async def get_sections(db: AsyncSession) -> list[models_campaign.Sections]:
    """Return all users from database"""

    result = await db.execute(select(models_campaign.Sections))
    return result.scalars().all()


async def add_section(db: AsyncSession, section: schemas_campaign.SectionBase) -> None:
    db_section = models_campaign.Sections(**section.dict())
    db.add(db_section)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("This name is already used")


async def delete_section(db: AsyncSession, section_name: str) -> None:
    await db.execute(
        delete(models_campaign.Sections).where(
            models_campaign.Sections.name == section_name
        )
    )
    await db.commit()


async def get_lists_from_section(
    db: AsyncSession, section_name: str
) -> list[models_campaign.Lists]:
    result = await db.execute(
        select(models_campaign.Lists).where(
            models_campaign.Lists.section_name == section_name
        )
    )
    lists = result.scalars().all()
    return lists


async def get_lists(db: AsyncSession) -> list[models_campaign.Lists]:
    result = await db.execute(select(models_campaign.Lists))
    lists = result.scalars().all()
    return lists
