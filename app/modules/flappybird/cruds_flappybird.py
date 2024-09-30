from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.flappybird import models_flappybird
from app.types.transactional_async_session import TransactionalAsyncSession


async def get_flappybird_score_leaderboard(
    db: AsyncSession,
) -> list[models_flappybird.FlappyBirdBestScore]:
    """Return the flappybird leaderboard scores"""
    result = await db.execute(
        select(models_flappybird.FlappyBirdBestScore)
        .order_by(models_flappybird.FlappyBirdBestScore.value.desc())
        .options(selectinload(models_flappybird.FlappyBirdBestScore.user)),
    )
    return list(result.scalars().all())


async def get_flappybird_personal_best_by_user_id(
    db: AsyncSession,
    user_id: str,
) -> models_flappybird.FlappyBirdBestScore | None:
    """Return the flappybird PB in the leaderboard by user_id"""

    personal_best_result = await db.execute(
        select(models_flappybird.FlappyBirdBestScore).where(
            models_flappybird.FlappyBirdBestScore.user_id == user_id,
        ),
    )
    return personal_best_result.scalar()


async def get_flappybird_score_position(
    db: AsyncSession,
    score_value: int,
) -> int | None:
    """Return the position in the leaderboard of a given score value"""

    result = await db.execute(
        select(func.count()).where(
            models_flappybird.FlappyBirdBestScore.value >= score_value,
        ),
    )

    return result.scalar()


async def create_flappybird_score(
    db: TransactionalAsyncSession,
    flappybird_score: models_flappybird.FlappyBirdScore,
) -> None:
    """Add a FlappyBirdScore in database"""
    db.add(flappybird_score)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def create_flappybird_best_score(
    db: TransactionalAsyncSession,
    flappybird_best_score: models_flappybird.FlappyBirdBestScore,
) -> None:
    """Add a FlappyBirdBestScore in database"""
    db.add(flappybird_best_score)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise


async def update_flappybird_best_score(
    db: AsyncSession,
    user_id: str,
    best_score: int,
):
    """Add a FlappyBirdBestScore in database"""
    await db.execute(
        update(models_flappybird.FlappyBirdBestScore)
        .where(
            models_flappybird.FlappyBirdBestScore.user_id == user_id,
        )
        .values(value=best_score),
    )
