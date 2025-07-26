from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.memberships import models_memberships, schemas_memberships
from app.core.users import schemas_users


async def get_association_memberships(
    db: AsyncSession,
) -> Sequence[schemas_memberships.MembershipSimple]:
    result = (
        (await db.execute(select(models_memberships.CoreAssociationMembership)))
        .scalars()
        .all()
    )
    return [
        schemas_memberships.MembershipSimple(
            name=membership.name,
            id=membership.id,
            manager_group_id=membership.manager_group_id,
        )
        for membership in result
    ]


async def get_association_membership_by_name(
    db: AsyncSession,
    name: str,
) -> schemas_memberships.MembershipSimple | None:
    result = (
        (
            await db.execute(
                select(models_memberships.CoreAssociationMembership).where(
                    models_memberships.CoreAssociationMembership.name == name,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_memberships.MembershipSimple(
            name=result.name,
            manager_group_id=result.manager_group_id,
            id=result.id,
        )
        if result
        else None
    )


async def get_association_membership_by_id(
    db: AsyncSession,
    membership_id: UUID,
) -> schemas_memberships.MembershipSimple | None:
    result = (
        (
            await db.execute(
                select(models_memberships.CoreAssociationMembership).where(
                    models_memberships.CoreAssociationMembership.id == membership_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_memberships.MembershipSimple(
            name=result.name,
            manager_group_id=result.manager_group_id,
            id=result.id,
        )
        if result
        else None
    )


async def create_association_membership(
    db: AsyncSession,
    membership: schemas_memberships.MembershipSimple,
):
    membership_db = models_memberships.CoreAssociationMembership(
        id=membership.id,
        name=membership.name,
        manager_group_id=membership.manager_group_id,
    )
    db.add(membership_db)


async def delete_association_membership(
    db: AsyncSession,
    membership_id: UUID,
):
    await db.execute(
        delete(models_memberships.CoreAssociationMembership).where(
            models_memberships.CoreAssociationMembership.id == membership_id,
        ),
    )


async def update_association_membership(
    db: AsyncSession,
    membership_id: UUID,
    membership: schemas_memberships.MembershipBase,
):
    await db.execute(
        update(models_memberships.CoreAssociationMembership)
        .where(models_memberships.CoreAssociationMembership.id == membership_id)
        .values(
            name=membership.name,
            manager_group_id=membership.manager_group_id,
        ),
    )


async def get_user_memberships_by_user_id(
    db: AsyncSession,
    user_id: str,
    minimal_start_date: date | None = None,
    maximal_start_date: date | None = None,
    minimal_end_date: date | None = None,
    maximal_end_date: date | None = None,
) -> Sequence[schemas_memberships.UserMembershipComplete]:
    result = (
        (
            await db.execute(
                select(models_memberships.CoreAssociationUserMembership).where(
                    models_memberships.CoreAssociationUserMembership.user_id == user_id,
                    models_memberships.CoreAssociationUserMembership.end_date
                    >= minimal_end_date
                    if minimal_end_date
                    else and_(True),
                    models_memberships.CoreAssociationUserMembership.end_date
                    <= maximal_end_date
                    if maximal_end_date
                    else and_(True),
                    models_memberships.CoreAssociationUserMembership.start_date
                    >= minimal_start_date
                    if minimal_start_date
                    else and_(True),
                    models_memberships.CoreAssociationUserMembership.start_date
                    <= maximal_start_date
                    if maximal_start_date
                    else and_(True),
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_memberships.UserMembershipComplete(
            id=membership.id,
            user_id=membership.user_id,
            association_membership_id=membership.association_membership_id,
            start_date=membership.start_date,
            end_date=membership.end_date,
            user=schemas_users.CoreUserSimple(
                id=membership.user.id,
                account_type=membership.user.account_type,
                school_id=membership.user.school_id,
                nickname=membership.user.nickname,
                firstname=membership.user.firstname,
                name=membership.user.name,
            ),
        )
        for membership in result
    ]


async def get_user_memberships_by_association_membership_id(
    db: AsyncSession,
    association_membership_id: UUID,
    minimal_start_date: date | None = None,
    maximal_start_date: date | None = None,
    minimal_end_date: date | None = None,
    maximal_end_date: date | None = None,
) -> Sequence[schemas_memberships.UserMembershipComplete]:
    result = (
        (
            await db.execute(
                select(models_memberships.CoreAssociationUserMembership).where(
                    models_memberships.CoreAssociationUserMembership.association_membership_id
                    == association_membership_id,
                    models_memberships.CoreAssociationUserMembership.end_date
                    >= minimal_end_date
                    if minimal_end_date
                    else and_(True),
                    models_memberships.CoreAssociationUserMembership.end_date
                    <= maximal_end_date
                    if maximal_end_date
                    else and_(True),
                    models_memberships.CoreAssociationUserMembership.start_date
                    >= minimal_start_date
                    if minimal_start_date
                    else and_(True),
                    models_memberships.CoreAssociationUserMembership.start_date
                    <= maximal_start_date
                    if maximal_start_date
                    else and_(True),
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_memberships.UserMembershipComplete(
            id=membership.id,
            user_id=membership.user_id,
            association_membership_id=membership.association_membership_id,
            start_date=membership.start_date,
            end_date=membership.end_date,
            user=schemas_users.CoreUserSimple(
                id=membership.user.id,
                account_type=membership.user.account_type,
                school_id=membership.user.school_id,
                nickname=membership.user.nickname,
                firstname=membership.user.firstname,
                name=membership.user.name,
            ),
        )
        for membership in result
    ]


async def get_user_memberships_by_user_id_and_association_membership_id(
    db: AsyncSession,
    user_id: str,
    association_membership_id: UUID,
) -> Sequence[schemas_memberships.UserMembershipComplete]:
    result = (
        (
            await db.execute(
                select(models_memberships.CoreAssociationUserMembership).where(
                    models_memberships.CoreAssociationUserMembership.user_id == user_id,
                    models_memberships.CoreAssociationUserMembership.association_membership_id
                    == association_membership_id,
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_memberships.UserMembershipComplete(
            id=membership.id,
            user_id=membership.user_id,
            association_membership_id=membership.association_membership_id,
            start_date=membership.start_date,
            end_date=membership.end_date,
            user=schemas_users.CoreUserSimple(
                id=membership.user.id,
                account_type=membership.user.account_type,
                school_id=membership.user.school_id,
                nickname=membership.user.nickname,
                firstname=membership.user.firstname,
                name=membership.user.name,
            ),
        )
        for membership in result
    ]


async def get_user_memberships_by_user_id_start_end_and_association_membership_id(
    db: AsyncSession,
    user_id: str,
    start_date: date,
    end_date: date,
    association_membership_id: UUID,
) -> Sequence[schemas_memberships.UserMembershipComplete]:
    result = (
        (
            await db.execute(
                select(models_memberships.CoreAssociationUserMembership).where(
                    models_memberships.CoreAssociationUserMembership.user_id == user_id,
                    models_memberships.CoreAssociationUserMembership.association_membership_id
                    == association_membership_id,
                    models_memberships.CoreAssociationUserMembership.start_date
                    == start_date,
                    models_memberships.CoreAssociationUserMembership.end_date
                    == end_date,
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        schemas_memberships.UserMembershipComplete(
            id=membership.id,
            user_id=membership.user_id,
            association_membership_id=membership.association_membership_id,
            start_date=membership.start_date,
            end_date=membership.end_date,
            user=schemas_users.CoreUserSimple(
                id=membership.user.id,
                account_type=membership.user.account_type,
                school_id=membership.user.school_id,
                nickname=membership.user.nickname,
                firstname=membership.user.firstname,
                name=membership.user.name,
            ),
        )
        for membership in result
    ]


async def get_user_membership_by_id(
    db: AsyncSession,
    user_membership_id: UUID,
) -> schemas_memberships.UserMembershipComplete | None:
    result = (
        (
            await db.execute(
                select(models_memberships.CoreAssociationUserMembership).where(
                    models_memberships.CoreAssociationUserMembership.id
                    == user_membership_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_memberships.UserMembershipComplete(
            id=result.id,
            user_id=result.user_id,
            association_membership_id=result.association_membership_id,
            start_date=result.start_date,
            end_date=result.end_date,
            user=schemas_users.CoreUserSimple(
                id=result.user.id,
                account_type=result.user.account_type,
                school_id=result.user.school_id,
                nickname=result.user.nickname,
                firstname=result.user.firstname,
                name=result.user.name,
            ),
        )
        if result
        else None
    )


async def create_user_membership(
    db: AsyncSession,
    user_membership: schemas_memberships.UserMembershipSimple,
):
    membership_db = models_memberships.CoreAssociationUserMembership(
        id=user_membership.id,
        user_id=user_membership.user_id,
        association_membership_id=user_membership.association_membership_id,
        start_date=user_membership.start_date,
        end_date=user_membership.end_date,
    )
    db.add(membership_db)


async def delete_user_membership(
    db: AsyncSession,
    user_membership_id: UUID,
):
    await db.execute(
        delete(models_memberships.CoreAssociationUserMembership).where(
            models_memberships.CoreAssociationUserMembership.id == user_membership_id,
        ),
    )


async def update_user_membership(
    db: AsyncSession,
    user_membership_id: UUID,
    user_membership_edit: schemas_memberships.UserMembershipEdit,
):
    await db.execute(
        update(models_memberships.CoreAssociationUserMembership)
        .where(
            models_memberships.CoreAssociationUserMembership.id == user_membership_id,
        )
        .values(**user_membership_edit.model_dump(exclude_none=True)),
    )
