from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.recommendation import models_recommendation, schemas_recommendation


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
    await db.commit()
    return recommendation


async def update_recommendation(
    recommendation_id: str,
    recommendation: schemas_recommendation.RecommendationEdit,
    db: AsyncSession,
):
    if not any(recommendation.model_dump().values()):
        return

    result = await db.execute(
        update(models_recommendation.Recommendation)
        .where(models_recommendation.Recommendation.id == recommendation_id)
        .values(**recommendation.model_dump(exclude_none=True)),
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
            models_recommendation.Recommendation.id == recommendation_id,
        ),
    )
    if result.rowcount == 1:
        await db.commit()
    else:
        await db.rollback()
        raise ValueError


async def get_recommendation_by_id(
    recommendation_id: str,
    db: AsyncSession,
) -> models_recommendation.Recommendation | None:
    result = await db.execute(
        select(models_recommendation.Recommendation).where(
            models_recommendation.Recommendation.id == recommendation_id,
        ),
    )
    return result.scalars().one_or_none()
