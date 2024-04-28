from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.flap import models_flappybird


async def get_flappybird_score_leaderboard(
    db: AsyncSession,
    skip: int,
    limit: int,
) -> list[models_flappybird.FlappyBirdScore]:
    """Return the flappybird leaderboard scores from postion skip to skip+limit"""
    result = await db.execute(
        select(models_flappybird.FlappyBirdScore)
        .options(selectinload(models_flappybird.FlappyBirdScore.user))
        .order_by(models_flappybird.FlappyBirdScore.value.desc())
        .offset(skip)
        .limit(limit),
    )
    return result.scalars().all()


async def get_flappybird_score_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> list[models_flappybird.FlappyBirdScore]:
    """Return all the flappybird scores by user_id"""

    result = await db.execute(
        select(models_flappybird.FlappyBirdScore).where(
            models_flappybird.FlappyBirdScore.user_id == user_id,
        ),
    )
    return result.scalars().all()


async def get_flappybird_pb_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> models_flappybird.FlappyBirdScore | None:
    """Return the flappybird PB in the leaderboard by user_id"""

    pb_result = await db.execute(
        select(models_flappybird.FlappyBirdScore)
        .where(models_flappybird.FlappyBirdScore.user_id == user_id)
        .order_by(models_flappybird.FlappyBirdScore.value.desc())
        .limit(1),
    )

    return pb_result.scalar()


async def get_flappybird_score_position(
    db: AsyncSession,
    score: models_flappybird.FlappyBirdScore,
) -> int | None:
    """Return the flappybird position in the leaderboard by user_id"""

    result = await db.execute(
        select(func.count())
        .select_from(models_flappybird.FlappyBirdScore)
        .order_by(models_flappybird.FlappyBirdScore.value.desc())
        .distinct(models_flappybird.FlappyBirdScore.user_id)
        .where(models_flappybird.FlappyBirdScore.value >= score.value),
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
