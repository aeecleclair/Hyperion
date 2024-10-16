import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.dependencies import get_db, is_user_a_member
from app.modules.flappybird import logic_flappybird, schemas_flappybird
from app.types.module import Module

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
async def get_flappybird_scores(db: AsyncSession = Depends(get_db)):
    """Return the leaderboard"""
    leaderboard = await logic_flappybird.get_flappybird_score_leaderboard(db=db)
    return leaderboard


@module.router.get(
    "/flappybird/scores/me",
    status_code=200,
    response_model=schemas_flappybird.FlappyBirdScoreCompleteFeedBack,
)
async def get_current_user_flappybird_personal_best(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    try:
        await logic_flappybird.get_current_user_flappybird_personnal_best(
            user=user, db=db
        )
    except logic_flappybird.FlappyBirdLogicException as e:
        raise HTTPException(
            status_code=404,
            detail=e.args,
        )


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
    db_flappybird_score = await logic_flappybird.create_flappybird_score(
        flappybird_score=flappybird_score, user=user, db=db
    )
    return db_flappybird_score
