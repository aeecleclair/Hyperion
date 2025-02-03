from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import models_core, schemas_core
from app.core.memberships import schemas_memberships


async def get_association_memberships(
    db: AsyncSession,
) -> Sequence[schemas_memberships.MembershipSimple]:
    result = (
        (await db.execute(select(models_core.CoreAssociationMembership)))
        .scalars()
        .all()
    )
    return [
        schemas_memberships.MembershipSimple(
            name=membership.name,
            id=membership.id,
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
                select(models_core.CoreAssociationMembership).where(
                    models_core.CoreAssociationMembership.name == name,
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_memberships.MembershipSimple(
            name=result.name,
            id=result.id,
        )
        if result
        else None
    )


async def get_association_membership_by_id(
    db: AsyncSession,
    membership_id: UUID,
) -> schemas_memberships.MembershipComplete | None:
    result = (
        (
            await db.execute(
                select(models_core.CoreAssociationMembership)
                .where(
                    models_core.CoreAssociationMembership.id == membership_id,
                )
                .options(
                    selectinload(models_core.CoreAssociationMembership.members),
                ),
            )
        )
        .scalars()
        .first()
    )
    return (
        schemas_memberships.MembershipComplete(
            name=result.name,
            id=result.id,
            members=[
                schemas_core.CoreUserSimple(
                    id=member.id,
                    account_type=member.account_type,
                    school_id=member.school_id,
                    nickname=member.nickname,
                    firstname=member.firstname,
                    name=member.name,
                )
                for member in result.members
            ],
        )
        if result
        else None
    )


def create_association_membership(
    db: AsyncSession,
    membership: schemas_memberships.MembershipComplete,
):
    membership_db = models_core.CoreAssociationMembership(
        id=membership.id,
        name=membership.name,
    )
    db.add(membership_db)


async def delete_association_membership(
    db: AsyncSession,
    membership_id: UUID,
):
    await db.execute(
        delete(models_core.CoreAssociationMembership).where(
            models_core.CoreAssociationMembership.id == membership_id,
        ),
    )


async def update_association_membership(
    db: AsyncSession,
    membership_id: UUID,
    membership: schemas_memberships.MembershipBase,
):
    await db.execute(
        update(models_core.CoreAssociationMembership)
        .where(models_core.CoreAssociationMembership.id == membership_id)
        .values(name=membership.name),
    )


async def get_user_memberships_by_user_id(
    db: AsyncSession,
    user_id: str,
    minimal_date: date | None = None,
) -> Sequence[schemas_memberships.UserMembershipComplete]:
    result = (
        (
            await db.execute(
                select(models_core.CoreAssociationUserMembership).where(
                    models_core.CoreAssociationUserMembership.user_id == user_id,
                    models_core.CoreAssociationUserMembership.end_date > minimal_date
                    if minimal_date
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
                select(models_core.CoreAssociationUserMembership).where(
                    models_core.CoreAssociationUserMembership.user_id == user_id
                    and models_core.CoreAssociationUserMembership.association_membership_id
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
                select(models_core.CoreAssociationUserMembership).where(
                    models_core.CoreAssociationUserMembership.id == user_membership_id,
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
        )
        if result
        else None
    )


def create_user_membership(
    db: AsyncSession,
    user_membership: schemas_memberships.UserMembershipComplete,
):
    membership_db = models_core.CoreAssociationUserMembership(
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
        delete(models_core.CoreAssociationUserMembership).where(
            models_core.CoreAssociationUserMembership.id == user_membership_id,
        ),
    )


async def update_user_membership(
    db: AsyncSession,
    user_membership_id: UUID,
    user_membership_edit: schemas_memberships.UserMembershipEdit,
):
    await db.execute(
        update(models_core.CoreAssociationUserMembership)
        .where(models_core.CoreAssociationUserMembership.id == user_membership_id)
        .values(**user_membership_edit.model_dump(exclude_none=True)),
    )
