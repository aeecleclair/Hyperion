import uuid
from datetime import datetime
from typing import Sequence
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.modules.recommendation import models_recommendation, schemas_recommendation


async def get_recommendation(
    db: AsyncSession,
) -> Sequence[models_recommendation.Recommendation]:
    result = await db.execute(select(models_recommendation.Recommendation))
    return result.scalars().all()


async def create_recommendation(
    recommendation: schemas_recommendation.RecommendationBase,
    db: AsyncSession,
    settings: Settings,
) -> models_recommendation.Recommendation:
    recommendation_db = models_recommendation.Recommendation(
        id=str(uuid.uuid4()),
        creation=datetime.now(ZoneInfo(settings.TIMEZONE)),
        **recommendation.model_dump(),
    )
    db.add(recommendation_db)
    await db.commit()
    return recommendation_db


async def update_recommendation(
    recommendation_id: str,
    recommendation: schemas_recommendation.RecommendationEdit,
    db: AsyncSession,
):
    result = await db.execute(
        update(models_recommendation.Recommendation)
        .where(models_recommendation.Recommendation.id == recommendation_id)
        .values(**recommendation.model_dump(exclude_none=True))
    )
    if result.rowcount == 1:
        await db.commit()
    else:
        await db.rollback()
        raise ValueError


async def delete_recommendation(
    recommendation_id: str,
    db: AsyncSession,
):
    result = await db.execute(
        delete(models_recommendation.Recommendation).where(
            models_recommendation.Recommendation.id == recommendation_id
        )
    )
    if result.rowcount == 1:
        await db.commit()
    else:
        await db.rollback()
        raise ValueError


async def get_recommendation_by_id(
    recommendation_id: str,
    db: AsyncSession,
) -> models_recommendation.Recommendation:
    result = await db.execute(
        select(models_recommendation.Recommendation).where(
            models_recommendation.Recommendation.id == recommendation_id
        )
    )
    try:
        return result.scalars().one()
    except NoResultFound:
        raise ValueError
