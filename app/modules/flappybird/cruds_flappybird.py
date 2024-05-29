import logging

from sqlalchemy import and_, desc, func, select
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
    subquery_max_score = (
        select(
            models_flappybird.FlappyBirdScore.user_id,
            func.max(models_flappybird.FlappyBirdScore.value).label("max_score"),
        )
        .group_by(models_flappybird.FlappyBirdScore.user_id)
        .cte("subquery_max_score")
    )
    # Subrequest to get (the best score of the user) id
    subquery_score_id = (
        select(
            models_flappybird.FlappyBirdScore.id,
            models_flappybird.FlappyBirdScore.user_id,
            models_flappybird.FlappyBirdScore.value,
        )
        .join(
            subquery_max_score,
            and_(
                models_flappybird.FlappyBirdScore.user_id
                == subquery_max_score.c.user_id,
                models_flappybird.FlappyBirdScore.value
                == subquery_max_score.c.max_score,
            ),
        )
        .order_by(
            models_flappybird.FlappyBirdScore.user_id,
            desc(models_flappybird.FlappyBirdScore.id),
        )
        .distinct(models_flappybird.FlappyBirdScore.user_id)
        .cte("subquery_score_id")
    )
    # Main request to get the best score of each user
    query = (
        select(models_flappybird.FlappyBirdScore)
        .join(
            subquery_score_id,
            models_flappybird.FlappyBirdScore.id == subquery_score_id.c.id,
        )
        .options(selectinload(models_flappybird.FlappyBirdScore.user))
        .order_by(models_flappybird.FlappyBirdScore.value.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
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
