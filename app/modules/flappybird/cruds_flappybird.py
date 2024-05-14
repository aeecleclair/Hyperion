import logging

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.flappybird import models_flappybird

hyperion_logger = logging.getLogger("hyperion.error")


async def get_flappybird_score_leaderboard(
    db: AsyncSession,
    skip: int,
    limit: int,
) -> list[models_flappybird.FlappyBirdScore]:
    """Return the flappybird leaderboard scores from postion skip to skip+limit"""
    subquery = (
        select(
            func.max(models_flappybird.FlappyBirdScore.value).label("max_score"),
            models_flappybird.FlappyBirdScore.user_id,
        )
        .group_by(models_flappybird.FlappyBirdScore.user_id)
        .alias("subquery")
    )

    result = await db.execute(
        select(models_flappybird.FlappyBirdScore)
        .join(
            subquery,
            and_(
                models_flappybird.FlappyBirdScore.user_id == subquery.c.user_id,
                models_flappybird.FlappyBirdScore.value == subquery.c.max_score,
            ),
        )
        .options(selectinload(models_flappybird.FlappyBirdScore.user))
        .order_by(models_flappybird.FlappyBirdScore.value.desc())
        .offset(skip)
        .limit(limit),
    )
    return list(result.scalars().all())


async def get_flappybird_personal_best_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> models_flappybird.FlappyBirdScore | None:
    """Return the flappybird PB in the leaderboard by user_id"""

    personal_best_result = await db.execute(
        select(models_flappybird.FlappyBirdScore)
        .where(models_flappybird.FlappyBirdScore.user_id == user_id)
        .order_by(models_flappybird.FlappyBirdScore.value.desc())
        .limit(1),
    )
    return personal_best_result.scalar()


async def get_flappybird_score_position(
    db: AsyncSession,
    score_value: int,
) -> int | None:
    """Return the position in the leaderboard of a given score value"""
    subquery = (
        select(
            func.max(models_flappybird.FlappyBirdScore.value).label("max_score"),
            models_flappybird.FlappyBirdScore.user_id,
        )
        .group_by(models_flappybird.FlappyBirdScore.user_id)
        .alias("subquery")
    )

    result = await db.execute(
        select(func.count())
        .select_from(subquery)
        .where(subquery.c.max_score >= score_value),
    )

    return result.scalar()


async def create_flappybird_score(
    db: AsyncSession,
    flappybird_score: models_flappybird.FlappyBirdScore,
) -> models_flappybird.FlappyBirdScore:
    """Add a FlappyBirdScore in database"""
    db.add(flappybird_score)
    try:
        await db.commit()
        return flappybird_score
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)
