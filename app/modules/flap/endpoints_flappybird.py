import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.flap import cruds_flappybird
from app.dependencies import get_db
from app.modules.flap import models_flappybird
from app.modules.flap import schemas_flappybird
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/flappybird/scores",
    response_model=list[schemas_flappybird.FlappyBirdScoreInDB],
    status_code=200,
    tags=[Tags.flappybird],
)
async def get_flappybird_score(
    skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)
):
    leaderboard = await cruds_flappybird.get_flappybird_score_leaderboard(
        db=db, skip=skip, limit=limit
    )
    return leaderboard


@router.get(
    "/flappybird/scores/{user_id}",
    response_model=list[schemas_flappybird.FlappyBirdScoreInDB],
    status_code=200,
    tags=[Tags.flappybird],
)
async def get_flappybird_score_by_user(
    user_id: str, db: AsyncSession = Depends(get_db)
):
    user_scores = await cruds_flappybird.get_flappybird_score_by_user_id(
        db=db, user_id=user_id
    )
    return user_scores


@router.post(
    "/flappybird/scores",
    response_model=schemas_flappybird.FlappyBirdScoreBase,
    status_code=201,
    tags=[Tags.flappybird],
)
async def create_flappybird_score(
    flappybird_score: schemas_flappybird.FlappyBirdScoreBase,
    db: AsyncSession = Depends(get_db),
):
    # Currently, flappybird_score is a schema instance
    # To add it to the database, we need to create a model

    # We need to generate a new UUID for the score
    score_id = str(uuid.uuid4())
    # And get the current date and time
    creation_time = datetime.now()

    db_flappybird_score = models_flappybird.FlappyBirdScore(
        id=score_id,
        user_id=flappybird_score.user_id,
        value=flappybird_score.value,
        creation_time=creation_time,
        # We add all informations contained in the schema
    )
    try:
        return await cruds_flappybird.create_flappybird_score(
            flappybird_score=db_flappybird_score, db=db
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
