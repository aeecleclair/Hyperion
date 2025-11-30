import json
import logging
import uuid
from datetime import UTC, datetime

import aiofiles
from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import GroupType
from app.core.users import cruds_users, models_users
from app.dependencies import (
    get_db,
    get_request_id,
    is_user_a_member,
    is_user_in,
)
from app.modules.campaign import (
    cruds_campaign,
    models_campaign,
    schemas_campaign,
)
from app.modules.campaign.factory_campaign import CampaignFactory
from app.modules.campaign.types_campaign import ListType, StatusType
from app.modules.campaign.user_deleter_campaign import user_deleter
from app.types import standard_responses
from app.types.content_type import ContentType
from app.types.module import Module
from app.utils.tools import (
    get_file_from_data,
    is_user_member_of_any_group,
    save_file_as_data,
)

module = Module(
    root="vote",
    tag="Campaign",
    default_allowed_groups_ids=[GroupType.AE],
    factory=CampaignFactory(),
    user_deleter=user_deleter,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


@module.router.get(
    "/campaign/sections",
    response_model=list[schemas_campaign.SectionComplete],
    status_code=200,
)
async def get_sections(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Return sections in the database as a list of `schemas_campaign.SectionBase`

    **The user must be a member of a group authorized to vote (voters) or a member of the group CAA to use this endpoint**
    """
    voters = await cruds_campaign.get_voters(db)
    voters_groups = [voter.group_id for voter in voters]
    voters_groups.append(GroupType.CAA)
    if not is_user_member_of_any_group(user, voters_groups):
        raise HTTPException(
            status_code=403,
            detail="Access forbidden : you are not a poll member",
        )

    return await cruds_campaign.get_sections(db)


@module.router.post(
    "/campaign/sections",
    response_model=schemas_campaign.SectionComplete,
    status_code=201,
)
async def add_section(
    section: schemas_campaign.SectionBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
):
    """
    Add a section.

    This endpoint can only be used in 'waiting' status.

    **The user must be a member of the group CAA to use this endpoint**
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

    await cruds_campaign.add_section(section=db_section, db=db)
    return db_section


@module.router.delete(
    "/campaign/sections/{section_id}",
    status_code=204,
)
async def delete_section(
    section_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
):
    """
    Delete a section.

    This endpoint can only be used in 'waiting' status.

    **The user must be a member of the group CAA to use this endpoint**
    """

    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=403,
            detail=f"You can't delete a section if the vote has already begun. The module status is {status} but should be 'waiting'",
        )

    await cruds_campaign.delete_section(section_id=section_id, db=db)


@module.router.get(
    "/campaign/lists",
    response_model=list[schemas_campaign.ListReturn],
    status_code=200,
)
async def get_lists(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Return campaign lists registered for the vote.

    **The user must be a member of a group authorized to vote (voters) or a member of the group CAA to use this endpoint**
    """
    voters = await cruds_campaign.get_voters(db)
    voters_groups = [voter.group_id for voter in voters]
    voters_groups.append(GroupType.CAA)
    if not is_user_member_of_any_group(user, voters_groups):
        raise HTTPException(
            status_code=403,
            detail="Access forbidden : you are not a poll member",
        )

    return await cruds_campaign.get_lists(db=db)


@module.router.post(
    "/campaign/lists",
    response_model=schemas_campaign.ListReturn,
    status_code=201,
)
async def add_list(
    campaign_list: schemas_campaign.ListBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
):
    """
    Add a campaign list to a section.

    This endpoint can only be used in 'waiting' status.

    **The user must be a member of the group CAA to use this endpoint**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=403,
            detail=f"You can't add a list if the vote has already begun. The module status is {status} but should be 'waiting'",
        )

    # Check if the section given exists in the DB.
    section = await cruds_campaign.get_section_by_id(
        db=db,
        section_id=campaign_list.section_id,
    )
    if section is None:
        raise HTTPException(status_code=404, detail="Given section doesn't exist.")

    if campaign_list.type == ListType.blank:
        raise HTTPException(
            status_code=400,
            detail="Blank list should not be added by an user. They will be created before the vote start.",
        )

    list_id = str(uuid.uuid4())

    # We don't need to add membership for list members by hand
    # SQLAlchemy will do it for us if we provide a `members` list
    members = []
    for member in campaign_list.members:
        if await cruds_users.get_user_by_id(db=db, user_id=member.user_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"User with id {member.user_id} doesn't exist.",
            )
        members.append(
            models_campaign.ListMemberships(
                user_id=member.user_id,
                role=member.role,
                list_id=list_id,
            ),
        )

    model_list = models_campaign.Lists(
        id=list_id,
        name=campaign_list.name,
        description=campaign_list.description,
        section_id=campaign_list.section_id,
        type=campaign_list.type,
        members=members,
        program=campaign_list.program,
    )

    await cruds_campaign.add_list(campaign_list=model_list, db=db)
    # We can't directly return the model_list because it doesn't have the relationships loaded
    return await cruds_campaign.get_list_by_id(db=db, list_id=list_id)


@module.router.delete(
    "/campaign/lists/{list_id}",
    status_code=204,
)
async def delete_list(
    list_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
):
    """
    Delete the campaign list with the given id.

    This endpoint can only be used in 'waiting' status.

    **The user must be a member of the group CAA to use this endpoint**
    """

    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=403,
            detail=f"You can't delete a list if the vote has already begun. The module status is {status} but should be 'waiting'",
        )

    await cruds_campaign.delete_list(list_id=list_id, db=db)


@module.router.delete(
    "/campaign/lists/",
    status_code=204,
)
async def delete_lists_by_type(
    list_type: ListType | None = None,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
):
    """
    Delete the all lists by type.

    This endpoint can only be used in 'waiting' status.

    **The user must be a member of the group CAA to use this endpoint**
    """

    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=403,
            detail=f"You can't delete a list if the vote has already begun. The module status is {status} but should be 'waiting'",
        )

    if list_type is None:
        for type_obj in ListType:
            await cruds_campaign.delete_list_by_type(list_type=type_obj, db=db)
    else:
        await cruds_campaign.delete_list_by_type(list_type=list_type, db=db)


@module.router.patch(
    "/campaign/lists/{list_id}",
    status_code=204,
)
async def update_list(
    list_id: str,
    campaign_list: schemas_campaign.ListEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
):
    """
    Update the campaign list with the given id.

    This endpoint can only be used in 'waiting' status.

    **The user must be a member of the group CAA to use this endpoint**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=403,
            detail=f"You can't edit a list if the vote has already begun. The module status is {status} but should be 'waiting'",
        )

    list_db = await cruds_campaign.get_list_by_id(db=db, list_id=list_id)
    if list_db is None:
        raise HTTPException(status_code=404, detail="List not found.")

    if campaign_list.members is not None:
        # We need to make sure the new list of members is valid
        for member in campaign_list.members:
            if await cruds_users.get_user_by_id(db=db, user_id=member.user_id) is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"User with id {member.user_id} doesn't exist.",
                )

    await cruds_campaign.update_list(
        list_id=list_id,
        campaign_list=campaign_list,
        db=db,
    )


@module.router.get(
    "/campaign/voters",
    response_model=list[schemas_campaign.VoterGroup],
    status_code=200,
)
async def get_voters(
    user: models_users.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the voters (groups allowed to vote) for the current campaign.
    """
    return await cruds_campaign.get_voters(db=db)


@module.router.post(
    "/campaign/voters",
    response_model=schemas_campaign.VoterGroup,
    status_code=201,
)
async def add_voter(
    voter: schemas_campaign.VoterGroup,
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
    db: AsyncSession = Depends(get_db),
):
    """
    Add voters (groups allowed to vote) for this campaign

    **The user must be a member of the group CAA to use this endpoint**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=400,
            detail=f"VoterGroups can only be edited in waiting mode. The current status is {status}",
        )

    db_voter = models_campaign.VoterGroups(**voter.model_dump(exclude_none=True))
    try:
        await cruds_campaign.add_voter(voter=db_voter, db=db)
    except IntegrityError as error:
        raise HTTPException(status_code=400, detail=str(error))
    return db_voter


@module.router.delete(
    "/campaign/voters/{group_id}",
    status_code=204,
)
async def delete_voter_by_group_id(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
):
    """
    Remove a voter by its group id

    **The user must be a member of the group CAA to use this endpoint**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=400,
            detail=f"VoterGroups can only be edited in waiting mode. The current status is {status}",
        )

    await cruds_campaign.delete_voter_by_group_id(group_id=group_id, db=db)


@module.router.delete(
    "/campaign/voters",
    status_code=204,
)
async def delete_voters(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
):
    """
    Remove voters (groups allowed to vote)

    **The user must be a member of the group CAA to use this endpoint**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=400,
            detail=f"VoterGroups can only be edited in waiting mode. The current status is {status}",
        )

    await cruds_campaign.delete_voters(db=db)


@module.router.post(
    "/campaign/status/open",
    status_code=204,
)
async def open_vote(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
):
    """
    If the status is 'waiting', change it to 'voting' and create the blank lists.

    > WARNING: this operation can not be reversed.
    > When the status is 'open', all users can vote and sections and lists can no longer be edited.

    **The user must be a member of the group CAA to use this endpoint**
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

    # Archive all changes to a json file
    lists = await cruds_campaign.get_lists(db=db)
    async with aiofiles.open(
        f"data/campaigns/lists-{datetime.now(tz=UTC).date().isoformat()}.json",
        mode="w",
    ) as file:
        await file.write(json.dumps([liste.as_dict() for liste in lists]))


@module.router.post(
    "/campaign/status/close",
    status_code=204,
)
async def close_vote(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
):
    """
    If the status is 'open', change it to 'closed'.

    > WARNING: this operation can not be reversed.
    > When the status is 'closed', users are no longer able to vote.

    **The user must be a member of the group CAA to use this endpoint**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.open:
        raise HTTPException(
            status_code=400,
            detail=f"The vote can only be closed if it is open. The current status is {status}",
        )

    await cruds_campaign.set_status(db=db, new_status=StatusType.closed)


@module.router.post(
    "/campaign/status/counting",
    status_code=204,
)
async def count_voting(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
):
    """
    If the status is 'closed', change it to 'counting'.

    > WARNING: this operation can not be reversed.
    > When the status is 'counting', administrators can see the results of the vote.

    **The user must be a member of the group CAA to use this endpoint**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.closed:
        raise HTTPException(
            status_code=400,
            detail=f"The vote can only be set to counting if it is closed. The current status is {status}",
        )

    await cruds_campaign.set_status(db=db, new_status=StatusType.counting)


@module.router.post(
    "/campaign/status/published",
    status_code=204,
)
async def publish_vote(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
):
    """
    If the status is 'counting', change it to 'published'.

    > WARNING: this operation can not be reversed.
    > When the status is 'published', everyone can see the results of the vote.

    **The user must be a member of the group CAA to use this endpoint**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.counting:
        raise HTTPException(
            status_code=400,
            detail=f"The vote can only be set to counting if it is closed. The current status is {status}",
        )

    await cruds_campaign.set_status(db=db, new_status=StatusType.published)


@module.router.post(
    "/campaign/status/reset",
    status_code=204,
)
async def reset_vote(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
):
    """
    Reset the vote. Can only be used if the current status is counting ou published.

    > WARNING: This will delete all votes then put the module to Waiting status. This will also delete blank lists.

    **The user must be a member of the group CAA to use this endpoint**
    """
    status = await cruds_campaign.get_status(db=db)
    if status not in [StatusType.published, StatusType.counting]:
        raise HTTPException(
            status_code=400,
            detail=f"The vote can only be reset in Published or Counting. The current status is {status}",
        )

    # Archive results to a json file
    results = await get_results(db=db, user=user)
    async with aiofiles.open(
        f"data/campaigns/results-{datetime.now(UTC).date().isoformat()}.json",
        mode="w",
    ) as file:
        await file.write(
            json.dumps(
                [{"list_id": res.list_id, "count": res.count} for res in results],
            ),
        )

    await cruds_campaign.reset_campaign(db=db)
    await cruds_campaign.set_status(
        db=db,
        new_status=StatusType.waiting,
    )


@module.router.post(
    "/campaign/votes",
    status_code=204,
)
async def vote(
    vote: schemas_campaign.VoteBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Add a vote for a given campaign list.

    An user can only vote for one list per section.

    **The user must be a member of a group authorized to vote (voters) to use this endpoint**
    """
    voters = await cruds_campaign.get_voters(db)
    voters_groups = [voter.group_id for voter in voters]
    if not is_user_member_of_any_group(user, voters_groups):
        raise HTTPException(
            status_code=403,
            detail="Access forbidden : you are not a poll member",
        )

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
        db=db,
        user_id=user.id,
        section_id=campaign_list.section_id,
    )
    if has_voted:
        raise HTTPException(
            status_code=400,
            detail="You have already voted for this section.",
        )

    # Add the vote to the db
    model_vote = models_campaign.Votes(
        id=str(uuid.uuid4()),
        list_id=vote.list_id,
    )

    # Mark user has voted for the given section.
    await cruds_campaign.mark_has_voted(
        db=db,
        user_id=user.id,
        section_id=campaign_list.section_id,
    )
    await cruds_campaign.add_vote(
        db=db,
        vote=model_vote,
    )


@module.router.get(
    "/campaign/votes",
    response_model=list[str],
    status_code=200,
)
async def get_sections_already_voted(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Return the list of id of sections an user has already voted for.

    **The user must be a member of a group authorized to vote (voters) to use this endpoint**
    """
    voters = await cruds_campaign.get_voters(db)
    voters_groups = [voter.group_id for voter in voters]
    if not is_user_member_of_any_group(user, voters_groups):
        raise HTTPException(
            status_code=403,
            detail="Access forbidden : you are not a poll member",
        )

    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.open:
        raise HTTPException(
            status_code=400,
            detail=f"You can only vote if the vote is open. The current status is {status}",
        )

    has_voted = await cruds_campaign.get_has_voted(db=db, user_id=user.id)
    return [section.section_id for section in has_voted]


@module.router.get(
    "/campaign/results",
    response_model=list[schemas_campaign.Result],
    status_code=200,
)
async def get_results(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Return the results of the vote.

    **The user must be a member of a group authorized to vote (voters) or a member of the group CAA to use this endpoint**
    """
    voters = await cruds_campaign.get_voters(db)
    voters_groups = [voter.group_id for voter in voters]
    voters_groups.append(GroupType.CAA)
    if not is_user_member_of_any_group(user, voters_groups):
        raise HTTPException(
            status_code=403,
            detail="Access forbidden : you are not a poll member",
        )

    status = await cruds_campaign.get_status(db=db)

    if (
        status == StatusType.counting
        and is_user_member_of_any_group(user, [GroupType.CAA])
    ) or status == StatusType.published:
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
                ),
            )
        return results
    raise HTTPException(
        status_code=400,
        detail=f"Results can only be acceded by admins in counting mode or by everyone in published mode. The current status is {status}",
    )


@module.router.get(
    "/campaign/status",
    response_model=schemas_campaign.VoteStatus,
    status_code=200,
)
async def get_status_vote(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Get the current status of the vote.

    **The user must be a member of a group authorized to vote (voters) or a member of the group CAA to use this endpoint**
    """
    voters = await cruds_campaign.get_voters(db)
    voters_groups = [voter.group_id for voter in voters]
    voters_groups.append(GroupType.CAA)
    if not is_user_member_of_any_group(user, voters_groups):
        raise HTTPException(
            status_code=403,
            detail="Access forbidden : you are not a poll member",
        )

    status = await cruds_campaign.get_status(db=db)
    return schemas_campaign.VoteStatus(status=status)


@module.router.get(
    "/campaign/stats/{section_id}",
    response_model=schemas_campaign.VoteStats,
    status_code=200,
)
async def get_stats_for_section(
    section_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
):
    """
    Get stats about a given section.

    **The user must be a member of the group CAA to use this endpoint**
    """
    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.open:
        raise HTTPException(
            status_code=400,
            detail=f"Stats can only be acceded during the vote. The current status is {status}",
        )
    count = await cruds_campaign.get_vote_count(db=db, section_id=section_id)
    return schemas_campaign.VoteStats(section_id=section_id, count=count)


@module.router.post(
    "/campaign/lists/{list_id}/logo",
    response_model=standard_responses.Result,
    status_code=201,
)
async def create_campaigns_logo(
    list_id: str,
    image: UploadFile = File(...),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.CAA)),
    request_id: str = Depends(get_request_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a logo for a campaign list.

    **The user must be a member of the group CAA to use this endpoint**
    """

    status = await cruds_campaign.get_status(db=db)
    if status != StatusType.waiting:
        raise HTTPException(
            status_code=400,
            detail=f"Lists can only be edited in waiting mode. The current status is {status}",
        )

    campaign_list = await cruds_campaign.get_list_by_id(db=db, list_id=list_id)
    if campaign_list is None:
        raise HTTPException(
            status_code=404,
            detail="The list does not exist.",
        )

    await save_file_as_data(
        upload_file=image,
        directory="campaigns",
        filename=str(list_id),
        max_file_size=4 * 1024 * 1024,
        accepted_content_types=[
            ContentType.jpg,
            ContentType.png,
            ContentType.webp,
        ],
    )

    return standard_responses.Result(success=True)


@module.router.get(
    "/campaign/lists/{list_id}/logo",
    response_class=FileResponse,
    status_code=200,
)
async def read_campaigns_logo(
    list_id: str,
    user: models_users.CoreUser = Depends(is_user_a_member),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the logo of a campaign list.
    **The user must be a member of a group authorized to vote (voters) or a member of the group CAA to use this endpoint**
    """
    voters = await cruds_campaign.get_voters(db)
    voters_groups = [voter.group_id for voter in voters]
    voters_groups.append(GroupType.CAA)
    if not is_user_member_of_any_group(user, voters_groups):
        raise HTTPException(
            status_code=403,
            detail="Access forbidden : you are not a poll member",
        )

    campaign_list = await cruds_campaign.get_list_by_id(db=db, list_id=list_id)
    if campaign_list is None:
        raise HTTPException(
            status_code=404,
            detail="The list does not exist.",
        )

    return get_file_from_data(
        directory="campaigns",
        filename=str(list_id),
        default_asset="assets/images/default_campaigns_logo.png",
    )
