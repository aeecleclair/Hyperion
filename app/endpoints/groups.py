"""
File defining the API itself, using fastAPI and schemas, and calling the cruds functions

Group management is part of the core of Hyperion. These endpoints allows to manage membership between users and groups.
"""


import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.cruds import cruds_groups, cruds_users
from app.dependencies import get_db, is_user_a_member_of
from app.models import models_core
from app.schemas import schemas_core
from app.utils.types.groups_type import GroupType
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/groups/",
    response_model=list[schemas_core.CoreGroupSimple],
    status_code=200,
    tags=[Tags.groups],
)
async def get_groups(
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Return all groups from database as a list of dictionaries

    **This endpoint is only usable by administrators**
    """

    groups = await cruds_groups.get_groups(db)
    return groups


@router.get(
    "/groups/{group_id}",
    response_model=schemas_core.CoreGroup,
    status_code=200,
    tags=[Tags.groups],
)
async def read_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Return group with id from database as a dictionary. This include a list of users being members of the group.

    **This endpoint is only usable by administrators**
    """

    db_group = await cruds_groups.get_group_by_id(db=db, group_id=group_id)
    if db_group is None:
        raise HTTPException(status_code=404, detail="Group not found")
    return db_group


@router.post(
    "/groups/",
    response_model=schemas_core.CoreGroupSimple,
    status_code=201,
    tags=[Tags.groups],
)
async def create_group(
    group: schemas_core.CoreGroupCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Create a new group.

    **This endpoint is only usable by administrators**
    """
    if await cruds_groups.get_group_by_name(group_name=group.name, db=db) is not None:
        raise HTTPException(
            status_code=400, detail="A group with the name {group.name} already exist"
        )

    try:
        db_group = models_core.CoreGroup(
            id=str(uuid.uuid4()),
            name=group.name,
            description=group.description,
        )
        return await cruds_groups.create_group(group=db_group, db=db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.patch(
    "/groups/{group_id}",
    response_model=schemas_core.CoreGroup,
    tags=[Tags.groups],
)
async def update_group(
    group_id: str,
    group_update: schemas_core.CoreGroupUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.admin)),
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

    return group


@router.delete(
    "/groups/{group_id}",
    status_code=204,
    tags=[Tags.groups],
)
async def delete_group(
    group_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Delete group from database.
    This will remove the group from all users but won't delete any user.

    `GroupTypes` groups can not be deleted.

    **This endpoint is only usable by administrators**
    """

    if group_id in GroupType:
        raise HTTPException(
            status_code=400, detail="GroupTypes groups can not be deleted"
        )

    await cruds_groups.delete_membership_by_group_id(group_id=group_id, db=db)
    await cruds_groups.delete_group(db=db, group_id=group_id)


@router.post(
    "/groups/membership",
    response_model=schemas_core.CoreGroup,
    status_code=201,
    tags=[Tags.groups],
)
async def create_membership(
    membership: schemas_core.CoreMembership,
    db: AsyncSession = Depends(get_db),
    user=Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Create a new membership in database and return the group. This allows to "add an user to a group".

    **This endpoint is only usable by administrators**
    """

    # We need to check provided ids are valid
    # TODO: use tools function
    if not await cruds_groups.get_group_by_id(group_id=membership.group_id, db=db):
        raise HTTPException(status_code=400, detail="Invalid group_id")
    if not await cruds_users.get_user_by_id(user_id=membership.user_id, db=db):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    try:
        membership_db = models_core.CoreMembership(
            user_id=membership.user_id,
            group_id=membership.group_id,
            description=membership.description,
        )
        return await cruds_groups.create_membership(db=db, membership=membership_db)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
