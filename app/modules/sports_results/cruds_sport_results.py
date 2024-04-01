from collections.abc import Sequence
from sqlite3 import IntegrityError

from sqlalchemy import delete, select
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


async def is_user_a_captain_of_a_sport(
    db: AsyncSession,
    user_id: str,
    sport: models_sport_results.Sport,
) -> bool:
    result = await db.execute(
        select(
            models_sport_results.CaptainMembership,
        ).where(
            models_sport_results.CaptainMembership.sport_id == sport.id,
            models_sport_results.CaptainMembership.user_id == user_id,
        ),
    )

    return result.unique().scalars().first() is not None


async def is_user_a_captain(
    db: AsyncSession,
    user_id: str,
) -> bool:
    result = await db.execute(
        select(
            models_sport_results.CaptainMembership,
        ).where(
            models_sport_results.CaptainMembership.user_id == user_id,
        ),
    )

    return result.unique().scalars().first() is not None


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


async def delete_result(
    result_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_results.Result).where(
            models_sport_results.Result.id == result_id,
        ),
    )
    await db.commit()


async def add_captain(
    db: AsyncSession,
    captain: models_sport_results.Captain,
) -> models_sport_results.Captain:
    db.add(captain)
    captain_membership = models_sport_results.CaptainMembership(
        user_id=captain.user_id,
        sport_id=captain.sport.id,
    )
    db.add(captain_membership)
    try:
        await db.commit()
        return captain
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def delete_captain(
    user_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_results.Captain).where(
            models_sport_results.Captain.user_id == user_id,
        ),
    )
    await db.execute(
        delete(models_sport_results.CaptainMembership).where(
            models_sport_results.CaptainMembership.user_id == user_id,
        ),
    )
    await db.commit()


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


async def delete_sport(
    sport_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_results.Sport).where(
            models_sport_results.Sport.id == sport_id,
        ),
    )
    await db.execute(
        delete(models_sport_results.Result).where(
            models_sport_results.Result.sport_id == sport_id,
        ),
    )
    await db.execute(
        delete(models_sport_results.CaptainMembership).where(
            models_sport_results.CaptainMembership.sport_id == sport_id,
        ),
    )
    await db.execute(
        delete(models_sport_results.Captain).where(
            models_sport_results.Captain.sport.id == sport_id,
        ),
    )
    await db.commit()
