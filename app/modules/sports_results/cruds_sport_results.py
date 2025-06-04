from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sports_results import models_sport_results, schemas_sport_results


async def get_sports(
    db: AsyncSession,
) -> Sequence[models_sport_results.Sport]:
    result = await db.execute(select(models_sport_results.Sport))
    return result.scalars().all()


async def get_sport_by_id(
    sport_id,
    db: AsyncSession,
) -> models_sport_results.Sport | None:
    result = await db.execute(
        select(models_sport_results.Sport).where(
            models_sport_results.Sport.id == sport_id,
        ),
    )
    return result.scalars().first()


async def get_captains_by_sport_id(
    sport_id: str,
    db: AsyncSession,
) -> Sequence[models_sport_results.Captain]:
    result = await db.execute(
        select(models_sport_results.Captain).where(
            models_sport_results.Captain.sports.id == sport_id,
        ),
    )
    return result.scalars().all()


async def is_user_a_captain_of_a_sport(
    user_id: str,
    sport_id: str,
    db: AsyncSession,
) -> bool:
    result = await db.execute(
        select(
            models_sport_results.Captain,
        ).where(
            models_sport_results.Captain.sports.any(
                models_sport_results.Captain.sports.id == sport_id,
            ),
            models_sport_results.Captain.user_id == user_id,
        ),
    )

    return result.unique().scalars().first() is not None


async def is_user_a_captain(
    user_id: str,
    db: AsyncSession,
) -> bool:
    result = await db.execute(
        select(
            models_sport_results.Captain,
        ).where(
            models_sport_results.Captain.user_id == user_id,
        ),
    )

    return result.unique().scalars().first() is not None


async def get_captain_by_id(
    captain_id,
    db: AsyncSession,
) -> models_sport_results.Captain | None:
    captain = await db.execute(
        select(models_sport_results.Captain).where(
            models_sport_results.Captain.id == captain_id,
        ),
    )
    return captain.scalars().first()


async def get_result_by_id(
    result_id,
    db: AsyncSession,
) -> models_sport_results.Result | None:
    result = await db.execute(
        select(models_sport_results.Result).where(
            models_sport_results.Result.id == result_id,
        ),
    )
    return result.scalars().first()


async def get_results(db: AsyncSession) -> Sequence[models_sport_results.Result]:
    result = await db.execute(
        select(models_sport_results.Result).order_by(
            models_sport_results.Result.match_date,
        ),
    )
    return result.scalars().all()


async def get_results_by_sport_id(
    sport_id,
    db: AsyncSession,
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


async def add_result(
    result: models_sport_results.Result,
    db: AsyncSession,
) -> models_sport_results.Result:
    db.add(result)
    try:
        await db.commit()
        return result
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def update_result(
    result_id: str,
    result_update: schemas_sport_results.ResultUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_results.Result)
        .where(
            models_sport_results.Result.id == result_id,
        )
        .values(**result_update.model_dump(exclude_none=True)),
    )
    await db.commit()


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
    captain: models_sport_results.Captain,
    db: AsyncSession,
) -> models_sport_results.Captain:
    db.add(captain)
    try:
        await db.commit()
        return captain
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def update_captain(
    captain_id: str,
    captain_update: schemas_sport_results.CaptainUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_results.Captain)
        .where(
            models_sport_results.Captain.id == captain_id,
        )
        .values(**captain_update.model_dump(exclude_none=True)),
    )
    await db.commit()


async def delete_captain(
    captain_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_results.Captain).where(
            models_sport_results.Captain.id == captain_id,
        ),
    )
    await db.commit()


async def add_sport(
    sport: models_sport_results.Sport,
    db: AsyncSession,
) -> models_sport_results.Sport:
    db.add(sport)
    try:
        await db.commit()
        return sport
    except IntegrityError as error:
        await db.rollback()
        raise ValueError(error)


async def update_sport(
    sport_id: str,
    sport_update: schemas_sport_results.SportUpdate,
    db: AsyncSession,
):
    await db.execute(
        update(models_sport_results.Sport)
        .where(
            models_sport_results.Sport.id == sport_id,
        )
        .values(**sport_update.model_dump(exclude_none=True)),
    )
    await db.commit()


async def delete_sport(
    sport_id: str,
    db: AsyncSession,
):
    await db.execute(
        delete(models_sport_results.Result).where(
            models_sport_results.Result.sport_id == sport_id,
        ),
    )
    await db.execute(
        #####################################
        delete(models_sport_results.Captain).where(
            models_sport_results.Captain.sports.id == sport_id,
        ),
    )
    await db.execute(
        delete(models_sport_results.Sport).where(
            models_sport_results.Sport.id == sport_id,
        ),
    )
    await db.commit()
