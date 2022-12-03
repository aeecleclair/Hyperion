import logging
import uuid
from os.path import exists

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_campaign, cruds_users
from app.dependencies import get_db, get_request_id, is_user_a_member_of
from app.models import models_campaign, models_core
from app.schemas import schemas_campaign
from app.utils.tools import save_file_to_the_disk
from app.utils.types import standard_responses
from app.utils.types.campaign_type import ListType, StatusType
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
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.student)),
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
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=403,
            detail=f"You can't add a section if the vote has already begun. The module status is {status} but should be 'waiting'",
        )

    db_section = models_campaign.Sections(
        id=str(uuid.uuid4()),
        name=section.name,
        description=section.description,
    )
    try:
        await cruds_campaign.add_section(section=db_section, db=db)
        return db_section
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.delete(
    "/campaign/sections/{section_id}",
    status_code=204,
    tags=[Tags.campaign],
)
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
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=403,
            detail=f"You can't delete a section if the vote has already begun. The module status is {status} but should be 'waiting'",
        )

    try:
        await cruds_campaign.delete_section(section_id=section_id, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.get(
    "/campaign/lists",
    response_model=list[schemas_campaign.ListReturn],
    status_code=200,
    tags=[Tags.campaign],
)
async def get_lists(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.student)),
):
    """Return lists"""
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
    """Allow an admin to add a campaign list to a section.

    **This endpoint is only usable by administrators**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=403,
            detail=f"You can't add a list if the vote has already begun. The module status is {status} but should be 'waiting'",
        )

    # Check if the section given exists in the DB.
    section = await cruds_campaign.get_section_by_id(db=db, section_id=list.section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Given section doesn't exist.")

    if list.type == ListType.blank:
        raise HTTPException(
            status_code=400,
            detail="Blank list should not be added by an user. They will be created before the vote start.",
        )

    list_id = str(uuid.uuid4())

    # We don't need to add membership for list members by hand
    # SQLAlchemy will do it for us if we provide a `members` list
    members = []
    for member in list.members:
        if await cruds_users.get_user_by_id(db=db, user_id=member.user_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"User with id {member.user_id} doesn't exist.",
            )
        members.append(
            models_campaign.ListMemberships(
                user_id=member.user_id,
                role=member.role,
            )
        )

    model_list = models_campaign.Lists(
        id=list_id,
        name=list.name,
        description=list.description,
        section_id=list.section_id,
        type=list.type,
        members=members,
    )
    try:
        await cruds_campaign.add_list(campaign_list=model_list, db=db)
        # We can't directly return the model_list because it doesn't have the relationships loaded
        return await cruds_campaign.get_list_by_id(db=db, list_id=list_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.delete(
    "/campaign/lists/{list_id}",
    status_code=204,
    tags=[Tags.campaign],
)
async def delete_list(
    list_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """Allow an admin to delete the list with the given id.

    **This endpoint is only usable by administrators**"""

    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=403,
            detail=f"You can't delete a list if the vote has already begun. The module status is {status} but should be 'waiting'",
        )

    try:
        await cruds_campaign.delete_list(list_id=list_id, db=db)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.patch(
    "/campaign/lists/{list_id}",
    status_code=204,
    tags=[Tags.campaign],
)
async def update_list(
    list_id: str,
    campaign_list: schemas_campaign.ListEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """Allow an admin to update the list with the given id.

    **This endpoint is only usable by administrators**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=403,
            detail=f"You can't edit a list if the vote has already begun. The module status is {status} but should be 'waiting'",
        )

    list = await cruds_campaign.get_list_by_id(db=db, list_id=list_id)
    if list is None:
        raise HTTPException(status_code=404, detail="List not found.")

    if campaign_list.members is not None:
        # We need to make sure the new list of members is valid
        for member in campaign_list.members:
            if await cruds_users.get_user_by_id(db=db, user_id=member.user_id) is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"User with id {member.user_id} doesn't exist.",
                )

    try:
        await cruds_campaign.update_list(
            list_id=list_id,
            campaign_list=campaign_list,
            db=db,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post(
    "/campaign/status/open",
    status_code=204,
    tags=[Tags.campaign],
)
async def open_voting(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    If the status is 'waiting', change it to 'voting' and create the blank lists.

    When the status is 'open', all users can vote and sections and lists can no longer be edited.

    **This endpoint is only usable by administrators**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=400,
            detail=f"The vote can only be open if it is waiting. The current status is {status}",
        )

    # Create the blank lists
    await cruds_campaign.add_blank_option(db=db)
    # Set the status to open
    await cruds_campaign.set_status(db=db, new_status=StatusType.open)


@router.post(
    "/campaign/status/close",
    status_code=204,
    tags=[Tags.campaign],
)
async def close_voting(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    If the status is 'open', change it to 'closed'.

    When the status is 'closed', users are no longer able to vote.

    **This endpoint is only usable by administrators**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.open:
        raise HTTPException(
            status_code=400,
            detail=f"The vote can only be closed if it is open. The current status is {status}",
        )

    await cruds_campaign.set_status(db=db, new_status=StatusType.closed)


@router.post(
    "/campaign/status/counting",
    status_code=204,
    tags=[Tags.campaign],
)
async def count_voting(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    If the status is 'closed', change it to 'counting'.

    When the status is 'counting', administrators can see the results of the vote.

    **This endpoint is only usable by administrators**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.closed:
        raise HTTPException(
            status_code=400,
            detail=f"The vote can only be set to counting if it is closed. The current status is {status}",
        )

    await cruds_campaign.set_status(db=db, new_status=StatusType.counting)


@router.post(
    "/campaign/status/reset",
    status_code=204,
    tags=[Tags.campaign],
)
async def reset_vote(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Reset the vote.

    WARNING: This will delete all votes, lists and sections. This will put the module to Waiting status.

    **This endpoint is only usable by administrators**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.counting:
        raise HTTPException(
            status_code=400,
            detail=f"The vote can only be reset in Counting status. The current status is {status}",
        )

    try:
        await cruds_campaign.reset_campaign(db=db)
        await cruds_campaign.set_status(
            db=db,
            new_status=StatusType.waiting,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.post(
    "/campaign/votes",
    status_code=204,
    tags=[Tags.campaign],
)
async def vote(
    vote: schemas_campaign.VoteBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.student)),
):
    """
    Add a vote

    An user can only vote for one list per section.
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.open:
        raise HTTPException(
            status_code=400,
            detail=f"You can only vote if the vote is open. The current status is {status}",
        )

    campaign_list = await cruds_campaign.get_list_by_id(db=db, list_id=vote.list_id)

    # Check if the campaign list exist.
    if campaign_list is None:
        raise HTTPException(status_code=404, detail="The list does not exist.")

    # Check if the user has already voted for this section.
    has_voted = await cruds_campaign.has_user_voted_for_section(
        db=db, user_id=user.id, section_id=campaign_list.section_id
    )
    if has_voted:
        raise HTTPException(
            status_code=400, detail="You have already voted for this section."
        )

    # Add the vote to the db
    model_vote = models_campaign.Votes(
        id=str(uuid.uuid4()),
        list_id=vote.list_id,
    )
    try:
        # Mark user has voted for the given section.
        await cruds_campaign.mark_has_voted(
            db=db, user_id=user.id, section_id=campaign_list.section_id
        )
        await cruds_campaign.add_vote(
            db=db,
            vote=model_vote,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get(
    "/campaign/votes",
    response_model=list[str],
    status_code=200,
    tags=[Tags.campaign],
)
async def get_sections_already_voted(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.student)),
):
    """
    Return the list of id of sections an user has already voted for.
    """

    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.open:
        raise HTTPException(
            status_code=400,
            detail=f"You can only vote if the vote is open. The current status is {status}",
        )

    has_voted = await cruds_campaign.get_has_voted(db=db, user_id=user.id)
    sections_ids = [section.section_id for section in has_voted]
    return sections_ids


@router.get(
    "/campaign/results",
    response_model=list[schemas_campaign.Result],
    status_code=200,
    tags=[Tags.campaign],
)
async def get_results(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Return the results of the vote.

    **This endpoint is only usable by administrators**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.counting:
        raise HTTPException(
            status_code=400,
            detail=f"Results can only be acceded in counting mode. The current status is {status}",
        )

    votes = await cruds_campaign.get_votes(db=db)

    count_by_list = {}
    for vote in votes:
        if vote.list_id not in count_by_list:
            count_by_list[vote.list_id] = 0

        count_by_list[vote.list_id] += 1

    results = []

    for list_id, count in count_by_list.items():
        results.append(
            schemas_campaign.Result(
                list_id=list_id,
                count=count,
            )
        )
    return results


@router.get(
    "/campaign/status",
    response_model=schemas_campaign.VoteStatus,
    status_code=200,
    tags=[Tags.campaign],
)
async def get_status_vote(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.student)),
):

    status = await cruds_campaign.get_status(db=db)
    return schemas_campaign.VoteStatus(status=status)


@router.post(
    "/campaign/lists/{list_id}/logo",
    response_model=standard_responses.Result,
    status_code=201,
    tags=[Tags.users],
)
async def create_campaigns_logo(
    list_id: str,
    image: UploadFile = File(...),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a logo for a list.

    **This endpoint is only usable by administrators**
    """

    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=400,
            detail=f"Results can only be acceded in waiting mode. The current status is {status}",
        )

    list = await cruds_campaign.get_list_by_id(db=db, list_id=list_id)
    if list is None:
        raise HTTPException(
            status_code=404,
            detail="The list does not exist.",
        )

    await save_file_to_the_disk(
        image=image,
        filename=f"campaigns/{list_id}.png",
        request_id=request_id,
        max_file_size=4 * 1024 * 1024,
        accepted_content_types=["image/jpeg", "image/png", "image/webp"],
    )

    return standard_responses.Result(success=True)


@router.get(
    "/campaign/lists/{list_id}/logo",
    response_class=FileResponse,
    status_code=200,
    tags=[Tags.users],
)
async def read_campaigns_logo(
    list_id: str,
    # TODO: we may want to remove this user requirement to be able to display images easily in html code
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.student)),
):

    if not exists(f"data/campaigns/{list_id}.png"):
        return FileResponse("assets/images/default_campaigns_logo.png")

    return FileResponse(f"data/campaigns/{list_id}.png")
