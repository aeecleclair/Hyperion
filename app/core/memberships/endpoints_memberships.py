import logging
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups import cruds_groups
from app.core.groups.groups_type import GroupType
from app.core.memberships import cruds_memberships, schemas_memberships
from app.core.memberships.utils_memberships import validate_user_new_membership
from app.core.users import cruds_users, models_users, schemas_users
from app.dependencies import (
    get_db,
    is_user,
    is_user_in,
)
from app.types.module import CoreModule

router = APIRouter(tags=["Memberships"])

hyperion_error_logger = logging.getLogger("hyperion.error")

core_module = CoreModule(
    root="memberships",
    tag="Memberships",
    router=router,
)


@router.get(
    "/memberships/",
    response_model=list[schemas_memberships.MembershipSimple],
    status_code=200,
)
async def read_associations_memberships(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user),
):
    """
    Return all memberships from database as a list of dictionaries
    """

    memberships = await cruds_memberships.get_association_memberships(db)
    return memberships


@router.get(
    "/memberships/{association_membership_id}/members",
    response_model=list[schemas_memberships.UserMembershipComplete],
    status_code=200,
)
async def read_association_membership(
    association_membership_id: uuid.UUID,
    minimalStartDate: date = Query(None),
    maximalStartDate: date = Query(None),
    minimalEndDate: date = Query(None),
    maximalEndDate: date = Query(None),
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Return membership with the given ID.

    **This endpoint is only usable by ECL members**
    """

    db_association_membership = (
        await cruds_memberships.get_association_membership_by_id(
            db=db,
            membership_id=association_membership_id,
        )
    )
    if db_association_membership is None:
        raise HTTPException(status_code=404, detail="Association Membership not found")

    if db_association_membership.manager_group_id not in [
        group.id for group in user.groups
    ] and GroupType.admin not in [group.id for group in user.groups]:
        raise HTTPException(
            status_code=403,
            detail="User is not allowed to access this membership",
        )

    db_user_memberships = (
        await cruds_memberships.get_user_memberships_by_association_membership_id(
            db=db,
            association_membership_id=association_membership_id,
            minimal_start_date=minimalStartDate,
            maximal_start_date=maximalStartDate,
            minimal_end_date=minimalEndDate,
            maximal_end_date=maximalEndDate,
        )
    )

    return db_user_memberships


@router.post(
    "/memberships/",
    response_model=schemas_memberships.MembershipSimple,
    status_code=201,
)
async def create_association_membership(
    membership: schemas_memberships.MembershipBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
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

    group = await cruds_groups.get_group_by_id(db, membership.manager_group_id)
    if group is None:
        raise HTTPException(
            status_code=404,
            detail="Group not found",
        )

    db_association_membership = schemas_memberships.MembershipSimple(
        name=membership.name,
        manager_group_id=membership.manager_group_id,
        id=uuid.uuid4(),
    )

    cruds_memberships.create_association_membership(
        db=db,
        membership=db_association_membership,
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    return db_association_membership


@router.patch(
    "/memberships/{association_membership_id}",
    status_code=204,
)
async def update_association_membership(
    association_membership_id: uuid.UUID,
    membership: schemas_memberships.MembershipBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Update a membership.

    **This endpoint is only usable by administrators**
    """
    db_association_membership = (
        await cruds_memberships.get_association_membership_by_id(
            db=db,
            membership_id=association_membership_id,
        )
    )
    if db_association_membership is None:
        raise HTTPException(status_code=404, detail="Association Membership not found")

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
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Delete a membership.

    **This endpoint is only usable by administrators**
    """
    db_association_membership = (
        await cruds_memberships.get_association_membership_by_id(
            db=db,
            membership_id=association_membership_id,
        )
    )
    if db_association_membership is None:
        raise HTTPException(status_code=404, detail="Association Membership not found")

    db_user_memberships = (
        await cruds_memberships.get_user_memberships_by_association_membership_id(
            db=db,
            association_membership_id=association_membership_id,
        )
    )
    if len(db_user_memberships) > 0:
        raise HTTPException(
            status_code=400,
            detail="Association Membership still has associated users",
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
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Return all memberships for a user.

    **This endpoint is only usable by administrators**
    """
    if user_id != user.id and GroupType.admin not in [
        group.id for group in user.groups
    ]:
        raise HTTPException(
            status_code=403,
            detail="User is not allowed to access other users' memberships",
        )

    memberships = await cruds_memberships.get_user_memberships_by_user_id(
        db,
        user_id,
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
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
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
    response_model=schemas_memberships.UserMembershipComplete,
    status_code=201,
)
async def create_user_membership(
    user_id: str,
    user_membership: schemas_memberships.UserMembershipBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Create a new user membership.

    **This endpoint is only usable by administrators**
    """

    db_association_membership = (
        await cruds_memberships.get_association_membership_by_id(
            db=db,
            membership_id=user_membership.association_membership_id,
        )
    )
    if db_association_membership is None:
        raise HTTPException(
            status_code=404,
            detail="Association membership not found",
        )

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
    await validate_user_new_membership(db_user_membership, db)

    cruds_memberships.create_user_membership(db=db, user_membership=db_user_membership)
    try:
        await db.commit()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to create user membership",
        )
    return schemas_memberships.UserMembershipComplete(
        **db_user_membership.__dict__,
        user=schemas_users.CoreUserSimple(
            name=db_user.name,
            id=db_user.id,
            firstname=db_user.firstname,
            nickname=db_user.nickname,
            account_type=db_user.account_type,
            school_id=db_user.school_id,
        ),
    )


@router.post(
    "/memberships/{association_membership_id}/add-batch/",
    status_code=201,
    response_model=list[schemas_memberships.MembershipUserMappingEmail],
)
async def add_batch_membership(
    association_membership_id: uuid.UUID,
    memberships_details: list[schemas_memberships.MembershipUserMappingEmail],
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Add a batch of user to a membership.

    Return the list of unknown users whose email is not in the database.

    **User must be an administrator to use this endpoint.**
    """
    db_association_membership = (
        await cruds_memberships.get_association_membership_by_id(
            db=db,
            membership_id=association_membership_id,
        )
    )
    if db_association_membership is None:
        raise HTTPException(
            status_code=400,
            detail="Association membership not found",
        )

    unknown_users: list[schemas_memberships.MembershipUserMappingEmail] = []
    for detail in memberships_details:
        detail_user = await cruds_users.get_user_by_email(
            db=db,
            email=detail.user_email,
        )
        if not detail_user:
            unknown_users.append(detail)
            continue
        stored_memberships = await cruds_memberships.get_user_memberships_by_user_id_start_end_and_association_membership_id(
            db=db,
            user_id=detail_user.id,
            association_membership_id=association_membership_id,
            start_date=detail.start_date,
            end_date=detail.end_date,
        )
        if len(stored_memberships) == 0:
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
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
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

    new_membership = schemas_memberships.UserMembershipSimple(
        id=db_user_membership.id,
        user_id=db_user_membership.user_id,
        association_membership_id=db_user_membership.association_membership_id,
        start_date=user_membership.start_date or db_user_membership.start_date,
        end_date=user_membership.end_date or db_user_membership.end_date,
    )

    await validate_user_new_membership(new_membership, db)

    await cruds_memberships.update_user_membership(
        db=db,
        user_membership_id=membership_id,
        user_membership_edit=user_membership,
    )

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise


@router.delete(
    "/memberships/users/{membership_id}",
    status_code=204,
)
async def delete_user_membership(
    membership_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
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
