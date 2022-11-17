import logging
import os
import shutil
import uuid
from os.path import exists

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_campaign
from app.dependencies import (
    get_db,
    get_request_id,
    is_user_a_member,
    is_user_a_member_of,
)
from app.models import models_campaign, models_core
from app.schemas import schemas_campaign
from app.utils.types import standard_responses
from app.utils.types.campaign_type import StatusType
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()

hyperion_error_logger = logging.getLogger("hyperion.error")


@router.get(
    "/campaign/sections",
    response_model=list[schemas_campaign.SectionComplete],
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


@router.post(
    "/campaign/sections",
    response_model=schemas_campaign.SectionComplete,
    status_code=201,
    tags=[Tags.campaign],
)
async def add_section(
    section: schemas_campaign.SectionBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Allow an admin to add a section of AEECL to the database.

    **This endpoint is only usable by administrators**
    """
    status = await cruds_campaign.get_status(db=db)
    if status.status == StatusType.waiting:
        db_section = models_campaign.Sections(id=str(uuid.uuid4()), **section.dict())
        try:
            await cruds_campaign.add_section(section=db_section, db=db)
            return db_section
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error))
    else:
        raise HTTPException(
            status_code=403,
            detail="You can't add a section if the vote has already begun",
        )


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
    status = await cruds_campaign.get_status(db=db)
    if status.status == StatusType.waiting:
        try:
            await cruds_campaign.delete_section(section_id=section_id, db=db)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error))
    else:
        raise HTTPException(
            status_code=403,
            detail="You can't delete a section if the vote has already begun",
        )


@router.get(
    "/campaign/sections/{section_id}/lists",
    response_model=list[schemas_campaign.ListReturn],
    status_code=200,
    tags=[Tags.campaign],
)
async def get_lists_from_section(
    section_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Return lists for the given section.
    """
    campaign_lists = await cruds_campaign.get_lists_from_section(
        section_id=section_id, db=db
    )
    return campaign_lists


@router.get(
    "/campaign/lists",
    response_model=list[schemas_campaign.ListReturn],
    status_code=200,
    tags=[Tags.campaign],
)
async def get_lists(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """Return list of campaing lists"""
    lists = await cruds_campaign.get_lists(db=db)
    return lists


@router.post(
    "/campaign/lists",
    response_model=schemas_campaign.ListReturn,
    status_code=201,
    tags=[Tags.campaign],
)
async def add_list(
    list: schemas_campaign.ListBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """Allow an admin to add a campaign list.

    **Only for admin users.**
    """
    status = await cruds_campaign.get_status(db=db)
    if status.status == StatusType.waiting:
        try:
            # Check if the section given exists in the DB.
            # Check if the section given exists in the DB.
            section = await cruds_campaign.get_section_by_name(
                db=db, section_id=list.section_id
            )
            if section is not None:
                model_campaign_list = schemas_campaign.ListComplete(
                    id=str(uuid.uuid4()),
                    **list.dict(),
                )
                try:
                    await cruds_campaign.add_list(
                        campaign_list=model_campaign_list, db=db
                    )
                    return await cruds_campaign.get_list_by_id(
                        db=db, list_id=model_campaign_list.id
                    )
                except ValueError as error:
                    raise HTTPException(status_code=422, detail=str(error))
            else:
                raise HTTPException(
                    status_code=404, detail="Given section doesn't exist."
                )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error))
    else:
        raise HTTPException(
            status_code=403,
            detail="You can't add a list if the vote has already begun",
        )


@router.delete("/campaign/lists/{list_id}", status_code=204, tags=[Tags.campaign])
async def delete_list(
    list_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """Allow an admin to delete the list with the given id.

    **Only for admin.**"""
    status = await cruds_campaign.get_status(db=db)
    if status.status == StatusType.waiting:
        try:
            await cruds_campaign.delete_list(list_id=list_id, db=db)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error))
    else:
        raise HTTPException(
            status_code=403,
            detail="You can't delete a list if the vote has already begun",
        )


@router.patch("/campaign/lists/{list_id}", status_code=201, tags=[Tags.campaign])
async def update_list(
    list_id: str,
    campaign_list: schemas_campaign.ListEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """Allow an admin to update the list with the given id.

    **Only for admins.**
    """
    status = await cruds_campaign.get_status(db=db)
    if status.status == StatusType.waiting:
        try:
            await cruds_campaign.update_list(
                list_id=list_id,
                campaign_list=campaign_list,
                db=db,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error))
    else:
        raise HTTPException(
            status_code=403,
            detail="You can't edit a list if the vote has already begun",
        )


@router.post("/campaign/votes/open", status_code=201, tags=[Tags.campaign])
async def open_voting(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    await cruds_campaign.add_blank_option(db=db)
    await cruds_campaign.set_status(
        db=db, new_status=schemas_campaign.VoteStatus(status=StatusType.opened)
    )


@router.post("/campaign/votes/close", status_code=201, tags=[Tags.campaign])
async def close_voting(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    await cruds_campaign.set_status(
        db=db, new_status=schemas_campaign.VoteStatus(status=StatusType.closed)
    )


@router.post(
    "/campaign/votes",
    status_code=201,
    tags=[Tags.campaign],
)
async def vote(
    vote: schemas_campaign.VoteBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """Add a vote."""
    try:
        status = await cruds_campaign.get_status(db=db)
        if status.status == StatusType.opened:
            campaign_list = await cruds_campaign.get_list_by_id(
                db=db, list_id=vote.list_id
            )

            # Check if the campaign list exist.
            if campaign_list is not None:
                # Check if the user has already vote for a list in the section.
                has_voted = await cruds_campaign.get_has_voted(
                    db=db, user_id=user.id, section_id=campaign_list.section_id
                )
                if has_voted is None:
                    # Mark user has voted for the given section.
                    await cruds_campaign.mark_has_voted(
                        db=db, user_id=user.id, section_id=campaign_list.section_id
                    )
                    # Add the vote to the db
                    model_vote = models_campaign.Votes(
                        id=str(uuid.uuid4()), **vote.dict()
                    )
                    try:
                        await cruds_campaign.add_vote(
                            db=db,
                            vote=model_vote,
                        )
                    except ValueError as error:
                        raise HTTPException(status_code=422, detail=str(error))
                else:
                    raise ValueError(
                        "User has already vote for a list in this section."
                    )
            else:
                raise ValueError("This list doesn't exist.")
        else:
            raise ValueError("Votes are closed.")
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get(
    "/campaign/votes",
    response_model=list[schemas_campaign.VoteBase],
    status_code=200,
    tags=[Tags.campaign],
)
async def get_results(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """Get all votes

    **Only for admin.**"""
    status = await cruds_campaign.get_status(db=db)
    if status.status == StatusType.closed or status == StatusType.counted:
        if status.status == StatusType.closed:
            await cruds_campaign.set_status(
                db=db, new_status=schemas_campaign.VoteStatus(status=StatusType.counted)
            )
        votes = await cruds_campaign.get_votes(db=db)
        return votes
    else:
        raise HTTPException(
            status_code=403,
            detail="You must close the vote before counting it",
        )


@router.get(
    "/campaign/votes/{section_id}",
    response_model=list[schemas_campaign.VoteBase],
    status_code=200,
    tags=[Tags.campaign],
)
async def get_results_by_section(
    section_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """Get all votes for a sections.

    **Only for admin.**
    """
    status = await cruds_campaign.get_status(db=db)
    if status.status == StatusType.closed or status == StatusType.counted:
        if status.status == StatusType.closed:
            await cruds_campaign.set_status(
                db=db, new_status=schemas_campaign.VoteStatus(status=StatusType.counted)
            )
        votes = await cruds_campaign.get_votes_for_section(db=db, section_id=section_id)
        return votes
    else:
        raise HTTPException(
            status_code=403,
            detail="You must close the vote before counting it",
        )


@router.get(
    "/campaign/status",
    response_model=schemas_campaign.VoteStatus,
    status_code=200,
    tags=[Tags.campaign],
)
async def get_status_vote(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):

    return await cruds_campaign.get_status(db=db)


@router.delete("/campaign/votes", status_code=204, tags=[Tags.campaign])
async def reset_vote(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """Delete all vote in the database."""
    status = await cruds_campaign.get_status(db=db)
    if status.status == StatusType.counted:
        try:
            await cruds_campaign.delete_votes(
                db=db,
            )
            await cruds_campaign.set_status(
                db=db, new_status=schemas_campaign.VoteStatus(status=StatusType.waiting)
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error))
    else:
        raise HTTPException(
            status_code=403,
            detail="You must count the votes before erasing it.",
        )


@router.post(
    "/campaign/{object_id}/logo",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users],
)
async def create_campaigns_logo(
    object_id: str,
    image: UploadFile = File(...),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    """Upload a logo for the campaign module. Can either be a section or a list logo."""
    status = await cruds_campaign.get_status(db=db)
    if status.status == StatusType.waiting:
        if image.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid file format, supported jpeg, png and webp",
            )

        # We need to go to the end of the file to be able to get the size of the file
        image.file.seek(0, os.SEEK_END)
        # Use file.tell() to retrieve the cursor's current position
        file_size = image.file.tell()  # Bytes
        print(file_size)
        if file_size > 1024 * 1024 * 4:  # 4 MB
            raise HTTPException(
                status_code=413,
                detail="File size is too big. Limit is 4 MB",
            )
        # We go back to the beginning of the file to save it on the disk
        await image.seek(0)

        try:
            with open(f"data/campaigns_logo/{object_id}.png", "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)

        except Exception as error:
            hyperion_error_logger.error(
                f"Create_campaigns_logo: could not save logo: {error} ({request_id})"
            )
            raise HTTPException(status_code=422, detail="Could not save logo")

        return standard_responses.Result(success=True)
    else:
        raise HTTPException(
            status_code=403,
            detail="You can't edit this if the vote has already begun",
        )


@router.get(
    "/campaign/{object_id}/logo",
    response_class=FileResponse,
    status_code=200,
    tags=[Tags.users],
)
async def read_campaigns_logo(
    object_id: str,
    # TODO: we may want to remove this user requirement to be able to display images easily in html code
    user: models_core.CoreUser = Depends(is_user_a_member),
):

    if not exists(f"data/campaigns_logo/{object_id}.png"):
        return FileResponse("assets/images/default_campaigns_logo.png")

    return FileResponse(f"data/campaigns_logo/{object_id}.png")


@router.post(
    "/campaign/{list_id}/group_photo",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users],
)
async def create_list_group_pictures(
    list_id: str,
    image: UploadFile = File(...),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    """Upload a list group photo."""
    status = await cruds_campaign.get_status(db=db)
    if status.status == StatusType.waiting:
        if image.content_type not in ["image/jpeg", "image/png", "image/webp"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid file format, supported jpeg, png and webp",
            )

        # We need to go to the end of the file to be able to get the size of the file
        image.file.seek(0, os.SEEK_END)
        # Use file.tell() to retrieve the cursor's current position
        file_size = image.file.tell()  # Bytes
        print(file_size)
        if file_size > 1024 * 1024 * 4:  # 4 MB
            raise HTTPException(
                status_code=413,
                detail="File size is too big. Limit is 4 MB",
            )
        # We go back to the beginning of the file to save it on the disk
        await image.seek(0)

        try:
            with open(
                f"data/campaigns_logo/list_group_pictures/{list_id}.png", "wb"
            ) as buffer:
                shutil.copyfileobj(image.file, buffer)

        except Exception as error:
            hyperion_error_logger.error(
                f"Create_campaigns_list_group_pictures: could not save logo: {error} ({request_id})"
            )
            raise HTTPException(status_code=422, detail="Could not save logo")

        return standard_responses.Result(success=True)
    else:
        raise HTTPException(
            status_code=403,
            detail="You can't edit this if the vote has already begun",
        )


@router.get(
    "/campaign/{list_id}/group_photo",
    response_class=FileResponse,
    status_code=200,
    tags=[Tags.users],
)
async def read_list_group_photo(
    list_id: str,
    # TODO: we may want to remove this user requirement to be able to display images easily in html code
    user: models_core.CoreUser = Depends(is_user_a_member),
):

    if not exists(f"data/campaigns_logo/list_group_pictures/{list_id}.png"):
        return FileResponse("assets/images/default_campaigns_logo.png")

    return FileResponse(f"data/campaigns_logo/list_group_pictures/{list_id}.png")
