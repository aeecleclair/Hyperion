import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
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

from app.types import standard_responses
from app.types.content_type import ContentType
from app.types.module import Module
from app.utils.tools import get_file_from_data, save_file_as_data

router = APIRouter()


class FeedbackPermissions(ModulePermissions):
    access_feedback = "access_feedback"
    manage_feedback = "manage_feedback"


module = Module(
    root="feedback",
    tag="Feedback",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=FeedbackFactory(),
    permissions=FeedbackPermissions,
)


@module.router.get(
    "/feedback/feedbacks",
    response_model=list[schemas_feedback.Feedback],
    status_code=200,
)
async def get_feedback(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([FeedbackPermissions.manage_feedback]),
    ),
):
    """
    Get feedbacks.

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_feedback.get_feedbacks(db=db)


@module.router.post(
    "/feedback/feedbacks",
    response_model=schemas_feedback.Feedback,
    status_code=201,
)
async def create_feedback(
    feedback: schemas_feedback.FeedbackBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([FeedbackPermissions.manage_feedback]),
    ),
):
    """
    Create a feedback.

    **This endpoint is only usable by members of the group BDE**
    """

    feedback_db = models_feedback.Feedback(
        id=uuid.uuid4(),
        creation=datetime.now(UTC),
        **feedback.model_dump(),
    )

    return await cruds_feedback.add_feedback(
        feedback=feedback_db,
        db=db,
    )




@module.router.delete(
    "/feedback/feedbacks/{feedback_id}",
    status_code=204,
)
async def delete_feedback(
    feedback_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([FeedbackPermissions.manage_feedback]),
    ),
):
    """
    Delete a feedback.

    **This endpoint is only usable by members of the group BDE**
    """

    try:
        await cruds_feedback.delete_feedback(
            db=db,
            feedback_id=feedback_id,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="The feedback does not exist")
