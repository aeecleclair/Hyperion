import uuid
from datetime import UTC, datetime

from app.core import models_core
from app.dependencies import AsyncDBSession
from app.modules.flappybird import (
    cruds_flappybird,
    models_flappybird,
    schemas_flappybird,
)


class FlappyBirdLogicException(Exception):
    def __init__(self):
        super().__init__()


class BestScoreNotFound(FlappyBirdLogicException):
    def __init__(self):
        super().__init__()


class ScorePositionNotFound(FlappyBirdLogicException):
    def __init__(self):
        super().__init__()


async def get_flappybird_score_leaderboard(db: AsyncDBSession):
    """Return the leaderboard"""
    leaderboard = await cruds_flappybird.get_flappybird_score_leaderboard(db=db)
    return leaderboard


async def get_current_user_flappybird_personnal_best(
    user: models_core.CoreUser,
    db: AsyncDBSession,
):
    user_personal_best_table = (
        await cruds_flappybird.get_flappybird_personal_best_by_user_id(
            db=db,
            user_id=user.id,
        )
    )
    if user_personal_best_table is None:
        raise BestScoreNotFound

    position = await cruds_flappybird.get_flappybird_score_position(
        db=db,
        score_value=user_personal_best_table.value,
    )
    if position is None:
        raise ScorePositionNotFound

    user_personal_best = schemas_flappybird.FlappyBirdScoreCompleteFeedBack(
        value=user_personal_best_table.value,
        user=user_personal_best_table.user,
        creation_time=user_personal_best_table.creation_time,
        position=position,
    )

    return user_personal_best


async def create_flappybird_score(
    flappybird_score: schemas_flappybird.FlappyBirdScoreBase,
    user: models_core.CoreUser,
    db: AsyncDBSession,
):
    # Currently, flappybird_score is a schema instance
    # To add it to the database, we need to create a model

    # We need to generate a new UUID for the score
    score_id = uuid.uuid4()
    # And get the current date and time
    creation_time = datetime.now(UTC)

    db_flappybird_score = models_flappybird.FlappyBirdScore(
        id=score_id,
        user_id=user.id,
        value=flappybird_score.value,
        creation_time=creation_time,
    )
    db_flappybird_best_score = models_flappybird.FlappyBirdBestScore(
        id=score_id,
        user_id=user.id,
        value=flappybird_score.value,
        creation_time=creation_time,
    )
    personal_best = await cruds_flappybird.get_flappybird_personal_best_by_user_id(
        db=db,
        user_id=user.id,
    )
    if personal_best is None:
        await cruds_flappybird.create_flappybird_best_score(
            flappybird_best_score=db_flappybird_best_score,
            db=db,
        )
    else:
        if personal_best.value < flappybird_score.value:
            await cruds_flappybird.update_flappybird_best_score(
                user_id=user.id,
                best_score=flappybird_score.value,
                db=db,
            )
        await cruds_flappybird.create_flappybird_score(
            flappybird_score=db_flappybird_score,
            db=db,
        )
    return db_flappybird_score


async def remove_flappybird_score(user_id: str, db: AsyncDBSession):
    await cruds_flappybird.delete_flappybird_best_score(user_id=user_id, db=db)
