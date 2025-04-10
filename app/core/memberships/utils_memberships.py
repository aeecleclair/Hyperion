from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.memberships import cruds_memberships, schemas_memberships


async def validate_user_membership(
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
