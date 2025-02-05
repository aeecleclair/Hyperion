import logging
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import models_core
from app.core.groups.groups_type import GroupType
from app.core.memberships import cruds_memberships, schemas_memberships
from app.core.users import cruds_users
from app.dependencies import (
    get_db,
    is_user,
    is_user_an_ecl_member,
    is_user_in,
)

router = APIRouter(tags=["Memberships"])

hyperion_error_logger = logging.getLogger("hyperion.error")


@router.get(
    "/memberships/",
    response_model=list[schemas_memberships.MembershipSimple],
    status_code=200,
)
async def read_associations_memberships(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Return all memberships from database as a list of dictionaries
    """

    memberships = await cruds_memberships.get_association_memberships(db)
    return memberships


@router.get(
    "/memberships/{membership_id}",
    response_model=schemas_memberships.MembershipComplete,
    status_code=200,
)
async def read_association_membership(
    membership_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_an_ecl_member),
):
    """
    Return membership with the given ID.

    **This endpoint is only usable by ECL members**
    """

    db_membership = await cruds_memberships.get_association_membership_by_id(
        db=db,
        membership_id=membership_id,
    )
    if db_membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")

    return db_membership


@router.post(
    "/memberships/",
    response_model=schemas_memberships.MembershipComplete,
    status_code=201,
)
async def create_association_membership(
    membership: schemas_memberships.MembershipBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Create a new membership.

    **This endpoint is only usable by administrators**
    """
    if await cruds_memberships.get_association_membership_by_name(
        name=membership.name,
        db=db,
    ):
        raise HTTPException(
            status_code=400,
            detail=f"A membership with the name {membership.name} already exists",
        )

    db_membership = schemas_memberships.MembershipComplete(
        name=membership.name,
        id=uuid.uuid4(),
    )

    cruds_memberships.create_association_membership(db=db, membership=db_membership)
    try:
        await db.commit()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to create membership",
        )
    return db_membership


@router.patch(
    "/memberships/{association_membership_id}",
    status_code=204,
)
async def update_association_membership(
    association_membership_id: uuid.UUID,
    membership: schemas_memberships.MembershipBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Update a membership.

    **This endpoint is only usable by administrators**
    """
    db_membership = await cruds_memberships.get_association_membership_by_id(
        db=db,
        membership_id=association_membership_id,
    )
    if db_membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")

    await cruds_memberships.update_association_membership(
        db=db,
        membership_id=association_membership_id,
        membership=membership,
    )

    try:
        await db.commit()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to update membership",
        )


@router.delete(
    "/memberships/{association_membership_id}",
    status_code=204,
)
async def delete_association_membership(
    association_membership_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Delete a membership.

    **This endpoint is only usable by administrators**
    """
    db_membership = await cruds_memberships.get_association_membership_by_id(
        db=db,
        membership_id=association_membership_id,
    )
    if db_membership is None:
        raise HTTPException(status_code=404, detail="Membership not found")

    if db_membership.users_memberships:
        raise HTTPException(
            status_code=400,
            detail="Membership still has members",
        )

    await cruds_memberships.delete_association_membership(
        db=db,
        membership_id=association_membership_id,
    )

    try:
        await db.commit()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete membership",
        )


@router.get(
    "/memberships/users/{user_id}",
    response_model=list[schemas_memberships.UserMembershipComplete],
    status_code=200,
)
async def read_user_memberships(
    user_id: str,
    minimalDate: str = Query(None),
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user()),
):
    """
    Return all memberships for a user.
    minimalDate is an optional parameter to filter memberships by their end date.
    format: YYYYMMDD

    **This endpoint is only usable by administrators**
    """
    if user_id != user.id and GroupType.admin not in [
        group.id for group in user.groups
    ]:
        raise HTTPException(
            status_code=403,
            detail="User is not allowed to access other users' memberships",
        )

    if minimalDate is not None and not re.match(r"^\d{8}$", minimalDate):
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Please use YYYYMMDD",
        )

    minimal_date = (
        datetime.strptime(minimalDate + "+0000", "%Y%m%d%z").date()
        if minimalDate
        else None
    )

    memberships = await cruds_memberships.get_user_memberships_by_user_id(
        db,
        user_id,
        minimal_date,
    )
    return memberships


@router.get(
    "/memberships/users/{user_id}/{association_membership_id}",
    response_model=list[schemas_memberships.UserMembershipComplete],
    status_code=200,
)
async def read_user_association_membership_history(
    user_id: str,
    association_membership_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Return all user memberships for a specific association membership for a user.

    **This endpoint is only usable by administrators**
    """

    memberships = await cruds_memberships.get_user_memberships_by_user_id_and_association_membership_id(
        db,
        user_id,
        association_membership_id,
    )
    return memberships


@router.post(
    "/memberships/users/{user_id}",
    response_model=schemas_memberships.UserMembershipSimple,
    status_code=201,
)
async def create_user_membership(
    user_id: str,
    user_membership: schemas_memberships.UserMembershipBase,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Create a new user membership.

    **This endpoint is only usable by administrators**
    """

    db_user = await cruds_users.get_user_by_id(db=db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    db_user_membership = schemas_memberships.UserMembershipSimple(
        id=uuid.uuid4(),
        user_id=user_id,
        association_membership_id=user_membership.association_membership_id,
        start_date=user_membership.start_date,
        end_date=user_membership.end_date,
    )

    cruds_memberships.create_user_membership(db=db, user_membership=db_user_membership)
    try:
        await db.commit()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to create user membership",
        )
    return db_user_membership


@router.post(
    "/memberships/{association_membership_id}/add-batch/",
    status_code=201,
    response_model=list[schemas_memberships.MembershipUserMappingEmail],
)
async def add_batch_membership(
    association_membership_id: uuid.UUID,
    memberships_details: list[schemas_memberships.MembershipUserMappingEmail],
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Add a batch of user to a membership.

    Return the list of unknown users whose email is not in the database.

    **User must be an administrator to use this endpoint.**
    """
    unknown_users: list[schemas_memberships.MembershipUserMappingEmail] = []
    for detail in memberships_details:
        detail_user = await cruds_users.get_user_by_email(
            db=db,
            email=detail.user_email,
        )
        if not detail_user:
            unknown_users.append(detail)
            continue
        stored_memberships = await cruds_memberships.get_user_memberships_by_user_id_and_association_membership_id(
            db=db,
            user_id=detail_user.id,
            association_membership_id=association_membership_id,
        )
        if not any(
            stored_membership.start_date == detail.start_date
            and stored_membership.end_date == detail.end_date
            for stored_membership in stored_memberships
        ):
            cruds_memberships.create_user_membership(
                db=db,
                user_membership=schemas_memberships.UserMembershipSimple(
                    id=uuid.uuid4(),
                    user_id=detail_user.id,
                    association_membership_id=association_membership_id,
                    start_date=detail.start_date,
                    end_date=detail.end_date,
                ),
            )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return unknown_users


@router.patch(
    "/memberships/users/{membership_id}",
    status_code=204,
)
async def update_user_membership(
    membership_id: uuid.UUID,
    user_membership: schemas_memberships.UserMembershipEdit,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Update a user membership.

    **This endpoint is only usable by administrators**
    """

    db_user_membership = await cruds_memberships.get_user_membership_by_id(
        db=db,
        user_membership_id=membership_id,
    )
    if db_user_membership is None:
        raise HTTPException(status_code=404, detail="User membership not found")

    await cruds_memberships.update_user_membership(
        db=db,
        user_membership_id=membership_id,
        user_membership_edit=user_membership,
    )

    try:
        await db.commit()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to update user membership",
        )


@router.delete(
    "/memberships/users/{membership_id}",
    status_code=204,
)
async def delete_user_membership(
    membership_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Delete a user membership.

    **This endpoint is only usable by administrators**
    """

    db_user_membership = await cruds_memberships.get_user_membership_by_id(
        db=db,
        user_membership_id=membership_id,
    )
    if db_user_membership is None:
        raise HTTPException(status_code=404, detail="User membership not found")

    await cruds_memberships.delete_user_membership(
        db=db,
        user_membership_id=membership_id,
    )

    try:
        await db.commit()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete user membership",
        )
