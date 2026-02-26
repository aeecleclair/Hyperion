import uuid
from datetime import UTC, datetime

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType
from app.core.permissions.type_permissions import ModulePermissions
from app.core.users import models_users
from app.dependencies import get_db, is_user_allowed_to
from app.modules.flappybird import (
    cruds_flappybird,
    models_flappybird,
    schemas_flappybird,
)
from app.types.module import Module


class FlappyBirdPermissions(ModulePermissions):
    access_flappybird = "access_flappybird"
    manage_flappybird = "manage_flappybird"


module = Module(
    root="flappybird",
    tag="Flappy Bird",
    default_allowed_account_types=[AccountType.student],
    factory=None,
    permissions=FlappyBirdPermissions,
)


@module.router.get(
    "/flappybird/scores",
    response_model=list[schemas_flappybird.FlappyBirdScoreInDB],
    status_code=200,
)
async def get_flappybird_score(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([FlappyBirdPermissions.access_flappybird]),
    ),
):
    """Return the leaderboard"""
    return await cruds_flappybird.get_flappybird_score_leaderboard(db=db)


@module.router.get(
    "/flappybird/scores/me",
    status_code=200,
    response_model=schemas_flappybird.FlappyBirdScoreCompleteFeedBack,
)
async def get_current_user_flappybird_personal_best(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([FlappyBirdPermissions.access_flappybird]),
    ),
):
    user_personal_best_table = (
        await cruds_flappybird.get_flappybird_personal_best_by_user_id(
            db=db,
            user_id=user.id,
        )
    )

    if user_personal_best_table is None:
        raise HTTPException(
            status_code=404,
            detail="Not found",
        )

    position = await cruds_flappybird.get_flappybird_score_position(
        db=db,
        score_value=user_personal_best_table.value,
    )
    if position is None:
        raise HTTPException(
            status_code=404,
            detail="Not found",
        )
    return schemas_flappybird.FlappyBirdScoreCompleteFeedBack(
        value=user_personal_best_table.value,
        user=user_personal_best_table.user,
        creation_time=user_personal_best_table.creation_time,
        position=position,
    )


@module.router.post(
    "/flappybird/scores",
    response_model=schemas_flappybird.FlappyBirdScoreBase,
    status_code=201,
)
async def create_flappybird_score(
    flappybird_score: schemas_flappybird.FlappyBirdScoreBase,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([FlappyBirdPermissions.access_flappybird]),
    ),
    db: AsyncSession = Depends(get_db),
):
    # Currently, flappybird_score is a schema instance
    # To add it to the database, we need to create a model

    # We need to generate a new UUID for the score
    score_id = uuid.uuid4()
    # And get the current date and time
    creation_time = datetime.now(UTC)

    db_flappybird_best_score = models_flappybird.FlappyBirdBestScore(
        id=score_id,
        user_id=user.id,
        value=flappybird_score.value,
        creation_time=creation_time,
    )
    personal_best = await cruds_flappybird.get_flappybird_personal_best_by_user_id(
        user_id=user.id,
        db=db,
    )
    if personal_best is None:
        await cruds_flappybird.create_flappybird_best_score(
            flappybird_best_score=db_flappybird_best_score,
            db=db,
        )
    elif personal_best.value < flappybird_score.value:
        await cruds_flappybird.update_flappybird_best_score(
            user_id=user.id,
            best_score=flappybird_score.value,
            db=db,
        )

    return db_flappybird_best_score


@module.router.delete(
    "/flappybird/scores/{targeted_user_id}",
    status_code=204,
)
async def remove_flappybird_score(
    targeted_user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([FlappyBirdPermissions.manage_flappybird]),
    ),
):
    await cruds_flappybird.delete_flappybird_best_score(db=db, user_id=targeted_user_id)
