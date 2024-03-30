from collections.abc import Sequence
from sqlite3 import IntegrityError

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sports_results import models_sport_results


async def get_sports(
    db: AsyncSession,
) -> Sequence[models_sport_results.Sport]:
    result = await db.execute(select(models_sport_results.Sport))
    return result.scalars().all()


async def get_captains_by_sport_id(
    db: AsyncSession,
    sport_id: str,
) -> Sequence[models_sport_results.Captain]:
    result = await db.execute(
        select(models_sport_results.Captain).where(
            models_sport_results.Captain.sport.id == sport_id,
        ),
    )
    return result.scalars().all()


async def get_results(db: AsyncSession) -> Sequence[models_sport_results.Result]:
    result = await db.execute(
        select(models_sport_results.Result).order_by(
            models_sport_results.Result.match_date,
        ),
    )
    return result.scalars().all()


async def get_results_by_sport_id(
    db: AsyncSession,
    sport_id,
) -> Sequence[models_sport_results.Result]:
    result = await db.execute(
        select(models_sport_results.Result)
        .where(
            models_sport_results.Result.sport_id == sport_id,
        )
        .order_by(
            models_sport_results.Result.match_date,
        ),
    )
    return result.scalars().all()


async def create_result(
    db: AsyncSession,
    result: models_sport_results.Result,
) -> models_sport_results.Result:
    db.add(result)
    try:
        await db.commit()
        return result
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def add_captain(
    db: AsyncSession,
    captain: models_sport_results.Captain,
) -> models_sport_results.Captain:
    db.add(captain)
    try:
        await db.commit()
        return captain
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def add_sport(
    db: AsyncSession,
    sport: models_sport_results.Sport,
) -> models_sport_results.Sport:
    db.add(sport)
    try:
        await db.commit()
        return sport
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)
