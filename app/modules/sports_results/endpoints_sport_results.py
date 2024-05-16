import uuid

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.core.module import Module
from app.dependencies import get_db, is_user_a_member
from app.modules.sports_results import (
    cruds_sport_results,
    models_sport_results,
    schemas_sport_results,
)

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
async def get_results_by_id(
    result_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_sport_results.get_results_by_id(result_id, db=db)


@module.router.get(
    "/sport-results/sports/",
    response_model=list[schemas_sport_results.Sport],
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
        return await cruds_sport_results.create_result(result=result_db, db=db)
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
    ) or not cruds_sport_results.is_user_a_captain_of_a_sport(
        user.id,
        result_update.sport_id,
        db,
    ):
        raise HTTPException(status_code=401, detail="Not a captain")

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
        raise HTTPException(status_code=401, detail="Not a captain")

    await cruds_sport_results.delete_result(
        result_id=result_id,
        db=db,
    )


@module.router.post(
    "/sport-results/sport",
    response_model=schemas_sport_results.Sport,
    status_code=201,
)
async def add_sport(
    result: schemas_sport_results.ResultBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    if not cruds_sport_results.is_user_a_captain_of_a_sport(
        user.id,
        result.sport_id,
        db,
    ):
        raise HTTPException(status_code=401, detail="Not a captain")

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
        return await cruds_sport_results.create_result(result=result_db, db=db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@module.router.patch(
    "/sport-results/{result_id}",
    status_code=204,
)
async def update_sport(
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
    ) or not cruds_sport_results.is_user_a_captain_of_a_sport(
        user.id,
        result_update.sport_id,
        db,
    ):
        raise HTTPException(status_code=401, detail="Not a captain")

    await cruds_sport_results.update_result(
        result_id=result_id,
        result_update=result_update,
        db=db,
    )


@module.router.delete(
    "/sport-results/{result_id}",
    status_code=204,
)
async def delete_sport(
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
        raise HTTPException(status_code=401, detail="Not a captain")

    await cruds_sport_results.delete_result(
        result_id=result_id,
        db=db,
    )
