import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.core.module import Module
from app.dependencies import get_db, is_user_a_member
from app.modules.sports_results import cruds_sport_results, schemas_sport_results

module = Module(
    root="sport-results",
    tag="Sport_results",
    default_allowed_groups_ids=[GroupType.student],
)


@module.router.get(
    "/sport-results/results/",
    response_model=list[schemas_sport_results.Result],
    status_code=200,
)
async def get_results(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_sport_results.get_results(db=db)


@module.router.get(
    "/sport-results/results/{sport_id}",
    response_model=list[schemas_sport_results.Result],
    status_code=200,
)
async def get_results_by_sport(
    sport_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return await cruds_sport_results.get_results_by_sport_id(sport_id, db=db)


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
