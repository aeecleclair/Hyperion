import uuid
from datetime import datetime
from typing import Sequence
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
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
        **recommendation.dict(),
    )
    db.add(recommendation_db)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)
    return recommendation_db


async def update_recommendation(
    recommendation_id: str,
    recommendation: schemas_recommendation.RecommendationEdit,
    db: AsyncSession,
):
    await db.execute(
        update(models_recommendation.Recommendation)
        .where(models_recommendation.Recommendation.id == recommendation_id)
        .values(**recommendation.dict(exclude_none=True))
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError()


async def delete_recommendation(
    recommendation_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_recommendation.Recommendation).where(
            models_recommendation.Recommendation.id == recommendation_id
        )
    )
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def get_recommendation_by_id(
    recommendation_id: str,
    db: AsyncSession,
) -> models_recommendation.Recommendation:
    result = await db.execute(
        select(models_recommendation.Recommendation).where(
            models_recommendation.Recommendation.id == recommendation_id
        )
    )
    return result.scalars().one()
