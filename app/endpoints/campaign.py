import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_campaign
from app.dependencies import get_db, is_user_a_member, is_user_a_member_of
from app.models import models_core
from app.schemas import schemas_campaign
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/campaign/sections",
    response_model=list[schemas_campaign.SectionBase],
    status_code=200,
    tags=[Tags.campaign],
)
async def get_sections(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return sections in the database as a list of `schemas_campaign.SectionBase`
    """
    sections = await cruds_campaign.get_sections(db)
    return sections


@router.post("/campaign/sections", status_code=201, tags=[Tags.campaign])
async def add_section(
    section: schemas_campaign.SectionBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Allow an admin to add a section of AEECL to the database.

    **This endpoint is only usable by administrators**
    """
    db_section = schemas_campaign.SectionComplete(
        id=str(uuid.uuid4()), **section.dict()
    )
    try:
        await cruds_campaign.add_section(section=db_section, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.delete("/campaign/sections/{section_id}", status_code=204, tags=[Tags.campaign])
async def delete_section(
    section_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Allow an admin to delete a section of AEECL from the database.

    **This endpoint is only usable by administrators**
    """
    try:
        await cruds_campaign.delete_section(section_id=section_id, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get(
    "/campaign/{sections_name}/lists",
    response_model=None,
    status_code=200,
    tags=[Tags.campaign],
)
async def get_lists_of_section(
    section_name: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return ""


@router.get(
    "/campaign/lists", response_model=None, status_code=200, tags=[Tags.campaign]
)
async def get_lists(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return ""


@router.post("/campaign/lists", status_code=201, tags=[Tags.campaign])
async def add_list(
    list: None,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    return ""


@router.delete("/campaign/lists/{list_id}", status_code=204, tags=[Tags.campaign])
async def delete_list(
    list_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    return ""


@router.patch("/campaign/lists/{list_id}", status_code=201, tags=[Tags.campaign])
async def update_list(
    list_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    return ""


@router.post("/campaign/votes", status_code=201, tags=[Tags.campaign])
async def vote(
    vote: None,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    return ""


@router.get(
    "/campaign/votes", response_model=None, status_code=200, tags=[Tags.campaign]
)
async def get_results(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    return ""


@router.patch("/campaign/votes/status", status_code=201, tags=[Tags.campaign])
async def toggle_vote(
    status: None,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    return ""


@router.post("/campaign/votes/reset", status_code=201, tags=[Tags.campaign])
async def reset_vote(
    status: None,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    return ""
