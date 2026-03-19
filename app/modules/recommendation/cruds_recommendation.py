import uuid
from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.recommendation import models_recommendation, schemas_recommendation

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult


async def get_recommendations(
    db: AsyncSession,
) -> Sequence[models_recommendation.Recommendation]:
    result = await db.execute(select(models_recommendation.Recommendation))
    return result.scalars().all()


async def create_recommendation(
    recommendation: models_recommendation.Recommendation,
    db: AsyncSession,
) -> models_recommendation.Recommendation:
    db.add(recommendation)
    await db.flush()
    return recommendation


async def update_recommendation(
    recommendation_id: uuid.UUID,
    recommendation: schemas_recommendation.RecommendationEdit,
    db: AsyncSession,
):
    if not bool(recommendation.model_fields_set):
        return

    result = await db.execute(
        update(models_recommendation.Recommendation)
        .where(models_recommendation.Recommendation.id == recommendation_id)
        .values(**recommendation.model_dump(exclude_none=True)),
    )
    if cast("CursorResult", result).rowcount == 1:
        await db.flush()
    else:
        await db.rollback()
        raise ValueError


async def delete_recommendation(
    recommendation_id: uuid.UUID,
    db: AsyncSession,
):
    result = await db.execute(
        delete(models_recommendation.Recommendation).where(
            models_recommendation.Recommendation.id == recommendation_id,
        ),
    )
    if cast("CursorResult", result).rowcount == 1:
        await db.flush()
    else:
        await db.rollback()
        raise ValueError


async def get_recommendation_by_id(
    recommendation_id: uuid.UUID,
    db: AsyncSession,
) -> models_recommendation.Recommendation | None:
    result = await db.execute(
        select(models_recommendation.Recommendation).where(
            models_recommendation.Recommendation.id == recommendation_id,
        ),
    )
    return result.scalars().one_or_none()
