from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.core.module import Module
from app.dependencies import get_db, is_user_a_member, is_user_a_member_of
from app.modules.recommendation import cruds_recommendation, schemas_recommendation

router = APIRouter()


module = Module(
    root="recommendation",
    tag="Recommendation",
    default_allowed_groups_ids=[GroupType.student, GroupType.staff],
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

    return await cruds_recommendation.get_recommendation(db=db)


@module.router.post(
    "/recommendation/recommendations",
    response_model=schemas_recommendation.Recommendation,
    status_code=201,
)
async def create_recommendation(
    recommendation: schemas_recommendation.RecommendationBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
):
    """
    Create a recommendation.

    **This endpoint is only usable by members of the group BDE**
    """

    try:
        return await cruds_recommendation.create_recommendation(
            recommendation=recommendation,
            db=db,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@module.router.patch(
    "/recommendation/recommendations/{recommendation_id}",
    status_code=204,
)
async def edit_recommendation(
    recommendation_id: str,
    recommendation: schemas_recommendation.RecommendationEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
):
    """
    Edit a recommendation.

    **This endpoint is only usable by members of the group BDE**
    """

    await cruds_recommendation.update_recommendation(
        recommendation_id=recommendation_id,
        recommendation=recommendation,
        db=db,
    )


@module.router.delete(
    "/recommendation/recommendations/{recommendation_id}",
    status_code=204,
)
async def delete_recommendation(
    recommendation_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.BDE)),
):
    """
    Delete a recommendation.

    **This endpoint is only usable by members of the group BDE**
    """

    await cruds_recommendation.delete_recommendation(
        db=db,
        recommendation_id=recommendation_id,
    )
