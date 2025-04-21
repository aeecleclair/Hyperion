from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.memberships import cruds_memberships, schemas_memberships


async def validate_user_new_membership(
    user_membership: schemas_memberships.UserMembershipSimple,
    db: AsyncSession,
) -> schemas_memberships.UserMembershipSimple:
    """
    Validate the given membership data.

    :param membership: The membership data to validate.
    :return: The validated membership data.
    """
    if user_membership.start_date > user_membership.end_date:
        raise HTTPException(
            status_code=400,
            detail="The start date must be before the end date.",
        )
    memberships = list(
        await cruds_memberships.get_user_memberships_by_user_id_and_association_membership_id(
            db,
            user_membership.user_id,
            user_membership.association_membership_id,
        ),
    )
    for membership in memberships:
        if user_membership.id != membership.id:
            if (
                user_membership.start_date
                < membership.end_date
                < user_membership.end_date
                or user_membership.start_date
                < membership.start_date
                < user_membership.end_date
                or membership.start_date
                < user_membership.end_date
                < membership.end_date
                or membership.start_date
                < user_membership.start_date
                < membership.end_date
            ):
                raise HTTPException(
                    status_code=400,
                    detail="The new membership period overlaps with an existing one.",
                )

    return user_membership


async def has_user_active_membership_to_association_membership(
    association_membership_id: UUID,
    user_id: str,
    db: AsyncSession,
) -> schemas_memberships.UserMembershipSimple:
    """
    Check if the user has an active membership to the association membership.
    :param membership_id: The ID of the membership to check.
    :param user_id: The ID of the user to check.
    :param db: The database session.
    :return: The active membership if found.
    :raises HTTPException: If the user does not have an active membership.
    """
    membership = await cruds_memberships.get_user_memberships_by_user_id_and_association_membership_id(
        db,
        user_id,
        association_membership_id,
    )
    current_membership = next(
        (
            membership
            for membership in membership
            if membership.start_date <= datetime.now(UTC).date() <= membership.end_date
        ),
        None,
    )
    if not current_membership:
        raise HTTPException(
            status_code=400,
            detail="The user does not have an active membership to the association membership.",
        )
    return current_membership
