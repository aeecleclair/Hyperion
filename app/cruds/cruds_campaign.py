from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import models_campaign


async def get_sections(db: AsyncSession) -> list[models_campaign.Sections]:
    """Return all users from database"""

    result = await db.execute(select(models_campaign.Sections))
    return result.scalars().all()
