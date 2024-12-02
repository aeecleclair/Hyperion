import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core, standard_responses
from app.core.groups.groups_type import AccountType, GroupType
from app.dependencies import (
    get_db,
    get_request_id,
    is_user_a_member,
    is_user_in,
)
from app.modules.recommendation import (
    cruds_recommendation,
    models_recommendation,
    schemas_recommendation,
)
from app.types.content_type import ContentType
from app.types.module import Module
from app.utils.tools import get_file_from_data, save_file_as_data

router = APIRouter()


module = Module(
    root="recommendation",
    tag="Recommendation",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
)


@module.router.get(
    "/recommendation/recommendations",
    response_model=list[schemas_recommendation.Recommendation],
    status_code=200,
)
async def get_recommendation(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get recommendations.

    **The user must be authenticated to use this endpoint**
    """

    return await cruds_recommendation.get_recommendations(db=db)


@module.router.post(
    "/recommendation/recommendations",
    response_model=schemas_recommendation.Recommendation,
    status_code=201,
)
async def create_recommendation(
    recommendation: schemas_recommendation.RecommendationBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.BDE)),
):
    """
    Create a recommendation.

    **This endpoint is only usable by members of the group BDE**
    """

    recommendation_db = models_recommendation.Recommendation(
        id=uuid.uuid4(),
        creation=datetime.now(UTC),
        **recommendation.model_dump(),
    )

    return await cruds_recommendation.create_recommendation(
        recommendation=recommendation_db,
        db=db,
    )


@module.router.patch(
    "/recommendation/recommendations/{recommendation_id}",
    status_code=204,
)
async def edit_recommendation(
    recommendation_id: uuid.UUID,
    recommendation: schemas_recommendation.RecommendationEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.BDE)),
):
    """
    Edit a recommendation.

    **This endpoint is only usable by members of the group BDE**
    """

    try:
        await cruds_recommendation.update_recommendation(
            recommendation_id=recommendation_id,
            recommendation=recommendation,
            db=db,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="The recommendation does not exist")


@module.router.delete(
    "/recommendation/recommendations/{recommendation_id}",
    status_code=204,
)
async def delete_recommendation(
    recommendation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.BDE)),
):
    """
    Delete a recommendation.

    **This endpoint is only usable by members of the group BDE**
    """

    try:
        await cruds_recommendation.delete_recommendation(
            db=db,
            recommendation_id=recommendation_id,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="The recommendation does not exist")


@module.router.get(
    "/recommendation/recommendations/{recommendation_id}/picture",
    response_class=FileResponse,
    status_code=200,
)
async def read_recommendation_image(
    recommendation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get the image of a recommendation.

    **The user must be authenticated to use this endpoint**
    """
    recommendation = await cruds_recommendation.get_recommendation_by_id(
        recommendation_id=recommendation_id,
        db=db,
    )

    if not recommendation:
        raise HTTPException(status_code=404, detail="The recommendation does not exist")

    return get_file_from_data(
        default_asset="assets/images/default_recommendation.png",
        directory="recommendations",
        filename=str(recommendation_id),
    )


@module.router.post(
    "/recommendation/recommendations/{recommendation_id}/picture",
    response_model=standard_responses.Result,
    status_code=201,
)
async def create_recommendation_image(
    recommendation_id: uuid.UUID,
    image: UploadFile = File(),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.BDE)),
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Add an image to a recommendation.

    **This endpoint is only usable by members of the group BDE**
    """
    recommendation = await cruds_recommendation.get_recommendation_by_id(
        recommendation_id=recommendation_id,
        db=db,
    )

    if not recommendation:
        raise HTTPException(status_code=404, detail="The recommendation does not exist")

    await save_file_as_data(
        upload_file=image,
        directory="recommendations",
        filename=str(recommendation_id),
        request_id=request_id,
        max_file_size=4 * 1024 * 1024,
        accepted_content_types=[
            ContentType.jpg,
            ContentType.png,
            ContentType.webp,
        ],
    )

    return standard_responses.Result(success=True)
