import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.core.module import Module
from app.dependencies import get_db, is_user_a_member
from app.modules.flap import cruds_flappybird, models_flappybird, schemas_flappybird

module = Module(
    root="flappybird",
    tag="Flappy Bird",
    default_allowed_groups_ids=[GroupType.student],
)


@module.router.get(
    "/flappybird/scores",
    response_model=list[schemas_flappybird.FlappyBirdScoreInDB],
    status_code=200,
)
async def get_flappybird_score(
    skip: int = 0,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    leaderboard = await cruds_flappybird.get_flappybird_score_leaderboard(
        db=db,
        skip=skip,
        limit=limit,
    )
    return leaderboard


@module.router.get(
    "/flappybird/scores/{user_id}",
    response_model=list[schemas_flappybird.FlappyBirdScoreInDB],
    status_code=200,
)
async def get_flappybird_score_by_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    user_scores = await cruds_flappybird.get_flappybird_score_by_user_id(
        db=db,
        user_id=user_id,
    )
    return user_scores


@module.router.get(
    "/flappybird/leaderboard/me",
    status_code=200,
    response_model=schemas_flappybird.FlappyBirdScoreCompleteFeedBack | None,
)
async def get_current_user_flappybird_pb(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    user_pb_table = await cruds_flappybird.get_flappybird_pb_by_user_id(
        db=db,
        user_id=user.id,
    )

    if user_pb_table is not None:
        position = await cruds_flappybird.get_flappybird_score_position(
            db=db,
            score=user_pb_table,
        )
        if position is not None:
            user_pb = schemas_flappybird.FlappyBirdScoreCompleteFeedBack(
                value=user_pb_table.value,
                user=user_pb_table.user,
                creation_time=user_pb_table.creation_time,
                position=position,
            )

            return user_pb
    return None


@module.router.post(
    "/flappybird/scores",
    response_model=schemas_flappybird.FlappyBirdScoreBase,
    status_code=201,
)
async def create_flappybird_score(
    flappybird_score: schemas_flappybird.FlappyBirdScoreBase,
    user: models_core.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    # Currently, flappybird_score is a schema instance
    # To add it to the database, we need to create a model

    # We need to generate a new UUID for the score
    score_id = str(uuid.uuid4())
    # And get the current date and time
    creation_time = datetime.now(UTC)

    db_flappybird_score = models_flappybird.FlappyBirdScore(
        id=score_id,
        user_id=user.id,
        value=flappybird_score.value,
        creation_time=creation_time,
        # We add all informations contained in the schema
    )
    try:
        return await cruds_flappybird.create_flappybird_score(
            flappybird_score=db_flappybird_score,
            db=db,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
