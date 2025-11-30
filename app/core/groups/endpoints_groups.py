"""
File defining the API itself, using fastAPI and schemas, and calling the cruds functions

Group management is part of the core of Hyperion. These endpoints allow managing membership between users and groups.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups import cruds_groups, models_groups, schemas_groups
from app.core.groups.factory_groups import CoreGroupsFactory
from app.core.groups.groups_type import GroupType
from app.core.groups.user_deleter_groups import user_deleter
from app.core.notification.utils_notification import get_topics_restricted_to_group_id
from app.core.users import cruds_users
from app.dependencies import (
    get_db,
    get_notification_manager,
    get_request_id,
    is_user_an_ecl_member,
    is_user_in,
)
from app.types.module import CoreModule
from app.utils.communication.notifications import NotificationManager

router = APIRouter(tags=["Groups"])

core_module = CoreModule(
    root="groups",
    tag="Groups",
    router=router,
    factory=CoreGroupsFactory(),
    user_deleter=user_deleter,
)

hyperion_security_logger = logging.getLogger("hyperion.security")


@router.get(
    "/groups/",
    response_model=list[schemas_groups.CoreGroupSimple],
    status_code=200,
)
async def read_groups(
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_an_ecl_member),
):
    """
    Return all groups from database as a list of dictionaries
    """

    return await cruds_groups.get_groups(db)


@router.get(
    "/groups/{group_id}",
    response_model=schemas_groups.CoreGroup,
    status_code=200,
)
async def read_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
):
    """
    Return group with id from database as a dictionary. This includes a list of users being members of the group.

    **This endpoint is only usable by administrators**
    """

    db_group = await cruds_groups.get_group_by_id(db=db, group_id=group_id)
    if db_group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return db_group


@router.post(
    "/groups/",
    response_model=schemas_groups.CoreGroupSimple,
    status_code=201,
)
async def create_group(
    group: schemas_groups.CoreGroupCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
):
    """
    Create a new group.

    **This endpoint is only usable by administrators**
    """
    if await cruds_groups.get_group_by_name(group_name=group.name, db=db) is not None:
        raise HTTPException(
            status_code=400,
            detail="A group with the name {group.name} already exist",
        )

    try:
        db_group = models_groups.CoreGroup(
            id=str(uuid.uuid4()),
            name=group.name,
            description=group.description,
        )
        return await cruds_groups.create_group(group=db_group, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch(
    "/groups/{group_id}",
    status_code=204,
)
async def update_group(
    group_id: str,
    group_update: schemas_groups.CoreGroupUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
):
    """
    Update the name or the description of a group.

    **This endpoint is only usable by administrators**
    """
    group = await cruds_groups.get_group_by_id(db=db, group_id=group_id)

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # If the request ask to update the group name, we need to check it is available
    if group_update.name and group_update.name != group.name:
        if (
            await cruds_groups.get_group_by_name(group_name=group_update.name, db=db)
            is not None
        ):
            raise HTTPException(
                status_code=400,
                detail="A group with the name {group.name} already exist",
            )

    await cruds_groups.update_group(db=db, group_id=group_id, group_update=group_update)


@router.post(
    "/groups/membership",
    response_model=schemas_groups.CoreGroup,
    status_code=201,
)
async def create_membership(
    membership: schemas_groups.CoreMembership,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
    request_id: str = Depends(get_request_id),
):
    """
    Create a new membership in database and return the group. This allows to "add a user to a group".

    **This endpoint is only usable by administrators**
    """

    # We need to check provided ids are valid
    # TODO: use tools function
    group_db = await cruds_groups.get_group_by_id(group_id=membership.group_id, db=db)
    if group_db is None:
        raise HTTPException(status_code=400, detail="Invalid group_id")
    user_db = await cruds_users.get_user_by_id(user_id=membership.user_id, db=db)
    if user_db is None:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    hyperion_security_logger.warning(
        f"Create_membership: Admin user {user.id} ({user.name}) added user {user_db.id} ({user_db.email}) to group {group_db.id} ({group_db.name}) ({request_id})",
    )

    membership_db = models_groups.CoreMembership(
        user_id=membership.user_id,
        group_id=membership.group_id,
        description=membership.description,
    )
    return await cruds_groups.create_membership(db=db, membership=membership_db)


@router.post(
    "/groups/batch-membership",
    status_code=204,
)
async def create_batch_membership(
    batch_membership: schemas_groups.CoreBatchMembership,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
    request_id: str = Depends(get_request_id),
):
    """
    Add a list of user to a group, using a list of email.
    If an user does not exist it will be ignored.

    **This endpoint is only usable by administrators**
    """

    group_db = await cruds_groups.get_group_by_id(
        group_id=batch_membership.group_id,
        db=db,
    )
    if group_db is None:
        raise HTTPException(status_code=400, detail="Invalid group_id")

    hyperion_security_logger.warning(
        f"Create_batch_membership: Admin user {user.id} ({user.name}) added users to group {group_db.id} ({group_db.name}) in batch ({request_id})",
    )

    for email in batch_membership.user_emails:
        user_db = await cruds_users.get_user_by_email(db=db, email=email)

        # We only want to add existing users to the group
        if user_db is not None:
            membership_db = models_groups.CoreMembership(
                user_id=user_db.id,
                group_id=batch_membership.group_id,
                description=batch_membership.description,
            )
            try:
                await cruds_groups.create_membership(db=db, membership=membership_db)
            except ValueError:
                pass

        # If the user does not exist, we will pass silently


@router.delete(
    "/groups/membership",
    status_code=204,
)
async def delete_membership(
    membership: schemas_groups.CoreMembershipDelete,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
    request_id: str = Depends(get_request_id),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    Delete a membership using the user and group ids.

    **This endpoint is only usable by administrators**
    """

    hyperion_security_logger.warning(
        f"Create_membership: Admin user {user.id} ({user.name}) removed user {membership.user_id} from group {membership.group_id} ({request_id})",
    )

    # To remove a user from a group, we should unsubscribe this user from all
    # topic that required to be a member of this group
    restricted_topics = await get_topics_restricted_to_group_id(
        group_id=membership.group_id,
        db=db,
    )
    for topic in restricted_topics:
        await notification_manager.unsubscribe_user_to_topic(
            topic_id=topic.id,
            user_id=membership.user_id,
            db=db,
        )

    await cruds_groups.delete_membership_by_group_and_user_id(
        group_id=membership.group_id,
        user_id=membership.user_id,
        db=db,
    )


@router.delete(
    "/groups/batch-membership",
    status_code=204,
)
async def delete_batch_membership(
    batch_membership: schemas_groups.CoreBatchDeleteMembership,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
    request_id: str = Depends(get_request_id),
    notification_manager: NotificationManager = Depends(get_notification_manager),
):
    """
    This endpoint removes all users from a given group.

    **This endpoint is only usable by administrators**
    """

    group_db = await cruds_groups.get_group_by_id(
        group_id=batch_membership.group_id,
        db=db,
    )
    if group_db is None:
        raise HTTPException(status_code=400, detail="Invalid group_id")

    # To remove a user from a group, we should unsubscribe this user from all
    # topic that required to be a member of this group
    restricted_topics = await get_topics_restricted_to_group_id(
        group_id=batch_membership.group_id,
        db=db,
    )
    for topic in restricted_topics:
        for user_from_group in group_db.members:
            await notification_manager.unsubscribe_user_to_topic(
                topic_id=topic.id,
                user_id=user_from_group.id,
                db=db,
            )

    hyperion_security_logger.warning(
        f"Create_batch_membership: Admin user {user.id} ({user.name}) removed all users from group {group_db.id} ({group_db.name}) in batch ({request_id})",
    )

    await cruds_groups.delete_membership_by_group_id(
        group_id=batch_membership.group_id,
        db=db,
    )


@router.delete(
    "/groups/{group_id}",
    status_code=204,
)
async def delete_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_in(GroupType.admin)),
):
    """
    Delete group from database.
    This will remove the group from all users but won't delete any user.

    `GroupTypes` groups can not be deleted.

    **This endpoint is only usable by administrators**
    """

    if group_id in set(item.value for item in GroupType):
        raise HTTPException(
            status_code=400,
            detail="GroupTypes groups can not be deleted",
        )

    await cruds_groups.delete_membership_by_group_id(group_id=group_id, db=db)
    await cruds_groups.delete_group(db=db, group_id=group_id)
