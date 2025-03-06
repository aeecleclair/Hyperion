import uuid

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.dependencies import get_db, is_user_a_member, is_user_a_member_of
from app.modules.sports_results import (
    cruds_sport_results,
    models_sport_results,
    schemas_sport_results,
)
from app.types.module import Module

module = Module(
    root="sport-results",
    tag="Sport_results",
    default_allowed_groups_ids=[GroupType.student],
)


@module.router.get(
    "/sport-results/results/",
    response_model=list[schemas_sport_results.ResultComplete],
    status_code=200,
)
async def get_results(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_sport_results.get_results(db=db)


@module.router.get(
    "/sport-results/results/sport/{sport_id}",
    response_model=list[schemas_sport_results.ResultComplete],
    status_code=200,
)
async def get_results_by_sport_id(
    sport_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_sport_results.get_results_by_sport_id(sport_id, db=db)


@module.router.get(
    "/sport-results/results/{result_id}",
    response_model=schemas_sport_results.ResultComplete,
    status_code=200,
)
async def get_result_by_id(
    result_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_sport_results.get_result_by_id(result_id, db=db)


@module.router.get(
    "/sport-results/sports/",
    response_model=list[schemas_sport_results.SportComplete],
    status_code=200,
)
async def get_sports(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_sport_results.get_sports(db=db)


@module.router.get(
    "/sport-results/captain/{user_id}",
    response_model=bool,
    status_code=200,
)
async def is_user_a_captain(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await cruds_sport_results.is_user_a_captain(user_id, db=db)


@module.router.get(
    "/sport-results/captain/{user_id}/{sport_id}",
    response_model=bool,
    status_code=200,
)
async def is_user_a_captain_of_a_sport(
    user_id: str,
    sport_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await cruds_sport_results.is_user_a_captain_of_a_sport(
        user_id,
        sport_id,
        db=db,
    )


@module.router.get(
    "/sport-results/captain/sport/{sport_id}",
    response_model=list[schemas_sport_results.CaptainComplete],
    status_code=200,
)
async def get_captains_by_sport_id(
    sport_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await cruds_sport_results.get_captains_by_sport_id(
        sport_id,
        db=db,
    )


@module.router.post(
    "/sport-results/captain",
    response_model=schemas_sport_results.CaptainBase,
    status_code=201,
)
async def add_captain(
    captain: schemas_sport_results.CaptainBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDS)),
):
    captain_complete = schemas_sport_results.CaptainComplete(
        id=str(uuid.uuid4()),
        **captain.model_dump(),
    )
    try:
        captain_db = models_sport_results.Captain(
            id=captain_complete.id,
            user_id=captain_complete.user_id,
            sports=captain_complete.sports,
        )
        return await cruds_sport_results.add_captain(captain=captain_db, db=db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@module.router.patch(
    "/sport-results/captain/{captain_id}",
    status_code=204,
)
async def update_captain(
    captain_id: str,
    captain_update: schemas_sport_results.CaptainUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDS)),
):
    captain = await cruds_sport_results.get_captain_by_id(captain_id=captain_id, db=db)
    if not captain:
        raise HTTPException(
            status_code=404,
            detail="Invalid id",
        )

    await cruds_sport_results.update_captain(
        captain_id=captain_id,
        captain_update=captain_update,
        db=db,
    )


@module.router.delete(
    "/sport-results/{captain_id}",
    status_code=204,
)
async def delete_captain(
    captain_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDS)),
):
    captain = await cruds_sport_results.get_captain_by_id(captain_id=captain_id, db=db)
    if not captain:
        raise HTTPException(
            status_code=404,
            detail="Invalid id",
        )

    await cruds_sport_results.delete_captain(
        captain_id=captain_id,
        db=db,
    )


@module.router.post(
    "/sport-results/result",
    response_model=schemas_sport_results.ResultComplete,
    status_code=201,
)
async def add_result(
    result: schemas_sport_results.ResultBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    if not cruds_sport_results.is_user_a_captain_of_a_sport(
        user.id,
        result.sport_id,
        db,
    ):
        raise HTTPException(status_code=403, detail="Not a captain")

    result_complete = schemas_sport_results.ResultComplete(
        id=str(uuid.uuid4()),
        **result.model_dump(),
    )
    try:
        result_db = models_sport_results.Result(
            id=result_complete.id,
            sport_id=result_complete.sport_id,
            score1=result_complete.score1,
            score2=result_complete.score2,
            rank=result_complete.rank,
            location=result_complete.location,
            match_date=result_complete.match_date,
        )
        return await cruds_sport_results.add_result(result=result_db, db=db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@module.router.patch(
    "/sport-results/result/{result_id}",
    status_code=204,
)
async def update_result(
    result_id: str,
    result_update: schemas_sport_results.ResultUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    result = await cruds_sport_results.get_result_by_id(result_id=result_id, db=db)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Invalid id",
        )

    if not cruds_sport_results.is_user_a_captain_of_a_sport(
        user.id,
        result.sport_id,
        db,
    ):
        raise HTTPException(status_code=403, detail="Not a captain")

    if result_update.sport_id and not cruds_sport_results.is_user_a_captain_of_a_sport(
        user.id,
        result_update.sport_id,
        db,
    ):
        raise HTTPException(status_code=403, detail="Not a captain")

    await cruds_sport_results.update_result(
        result_id=result_id,
        result_update=result_update,
        db=db,
    )


@module.router.delete(
    "/sport-results/result/{result_id}",
    status_code=204,
)
async def delete_result(
    result_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    result = await cruds_sport_results.get_result_by_id(result_id=result_id, db=db)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Invalid id",
        )

    if not cruds_sport_results.is_user_a_captain_of_a_sport(
        user.id,
        result.sport_id,
        db,
    ):
        raise HTTPException(status_code=403, detail="Not a captain")

    await cruds_sport_results.delete_result(
        result_id=result_id,
        db=db,
    )


@module.router.post(
    "/sport-results/sport/",
    response_model=schemas_sport_results.SportComplete,
    status_code=201,
)
async def add_sport(
    sport: schemas_sport_results.SportBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDS)),
):
    sport_complete = schemas_sport_results.SportComplete(
        id=str(uuid.uuid4()),
        **sport.model_dump(),
    )
    try:
        sport_db = models_sport_results.Sport(
            id=sport_complete.id,
            name=sport_complete.name,
            captains=sport_complete.captains,
        )
        return await cruds_sport_results.add_sport(sport=sport_db, db=db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@module.router.patch(
    "/sport-results/sport/{sport_id}",
    status_code=204,
)
async def update_sport(
    sport_id: str,
    sport_update: schemas_sport_results.SportUpdate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDS)),
):
    sport = await cruds_sport_results.get_sport_by_id(sport_id=sport_id, db=db)
    if not sport:
        raise HTTPException(
            status_code=404,
            detail="Invalid id",
        )

    await cruds_sport_results.update_sport(
        sport_id=sport_id,
        sport_update=sport_update,
        db=db,
    )


@module.router.delete(
    "/sport-results/sport/{sport_id}",
    status_code=204,
)
async def delete_sport(
    sport_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDS)),
):
    sport = await cruds_sport_results.get_sport_by_id(sport_id=sport_id, db=db)
    if not sport:
        raise HTTPException(
            status_code=404,
            detail="Invalid id",
        )

    await cruds_sport_results.delete_sport(
        sport_id=sport_id,
        db=db,
    )