import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType
from app.core.permissions.type_permissions import ModulePermissions
from app.core.users import models_users
from app.dependencies import (
    get_db,
    is_user_allowed_to,
)
from app.modules.feedback import (
    cruds_feedback,
    models_feedback,
    schemas_feedback,
)
from app.types.module import Module

router = APIRouter()


class FeedbackPermissions(ModulePermissions):
    access_feedback = "access_feedback"
    manage_feedback = "manage_feedback"


module = Module(
    root="feedback",
    tag="Feedback",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=None,
    permissions=FeedbackPermissions,
)


@module.router.get(
    "/feedback/feedbacks",
    response_model=list[schemas_feedback.Feedback],
    status_code=200,
)
async def get_feedbacks(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to(
            [FeedbackPermissions.access_feedback]
        ),  # todo : manage_feedback permission
    ),
):
    """
    Get all feedbacks.
    **The user must be authenticated to use this endpoint**
    """

    return await cruds_feedback.get_feedbacks(db=db)


@module.router.post(
    "/feedback/feedbacks",
    status_code=201,
)
async def create_feedback(
    feedback: schemas_feedback.FeedbackBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([FeedbackPermissions.access_feedback]),
    ),
):
    """
    Creates a feedback.
    **The user must be authenticated to use this endpoint**
    """

    await cruds_feedback.add_feedback(
        feedback=feedback,
        db=db,
        user_id=user.id,
        id=uuid.uuid4(),
    )


@module.router.delete(
    "/feedback/feedbacks/{feedback_id}",
    status_code=204,
)
async def delete_feedback(
    feedback_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to(
            [FeedbackPermissions.access_feedback]
        ),  # todo : manage_feedback permission
    ),
):
    """
    Deletes a feedback.
    **The user must be authenticated to use this endpoint**
    """

    try:
        await cruds_feedback.delete_feedback(
            db=db,
            feedback_id=feedback_id,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="The feedback does not exist")
