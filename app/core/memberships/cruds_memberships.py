from datetime import date
from uuid import UUID

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.documents.types_documenso import DocumentStatus
from app.core.memberships import models_memberships, schemas_memberships
from app.core.memberships.utils_memberships import (
    membership_complete_model_to_schema,
    membership_model_to_schema,
    user_membership_complete_model_to_schema,
    user_membership_with_association_model_to_schema,
)


async def get_association_memberships(
    db: AsyncSession,
) -> list[schemas_memberships.MembershipSimple]:
    result = (
        (await db.execute(select(models_memberships.CoreAssociationMembership)))
        .scalars()
        .all()
    )
    return [membership_model_to_schema(membership) for membership in result]


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
    return membership_model_to_schema(result) if result else None


async def get_association_membership_by_id(
    db: AsyncSession,
    membership_id: UUID,
) -> schemas_memberships.MembershipComplete | None:
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
    return membership_complete_model_to_schema(result) if result else None


async def create_association_membership(
    db: AsyncSession,
    membership: schemas_memberships.MembershipSimple,
):
    membership_db = models_memberships.CoreAssociationMembership(
        id=membership.id,
        name=membership.name,
        manager_group_id=membership.manager_group_id,
        template_id=membership.template_id,
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
    membership: schemas_memberships.MembershipEdit,
):
    await db.execute(
        update(models_memberships.CoreAssociationMembership)
        .where(models_memberships.CoreAssociationMembership.id == membership_id)
        .values(
            **membership.model_dump(exclude_unset=True),
        ),
    )


async def get_user_memberships_by_user_id(
    db: AsyncSession,
    user_id: str,
    minimal_start_date: date | None = None,
    maximal_start_date: date | None = None,
    minimal_end_date: date | None = None,
    maximal_end_date: date | None = None,
    manager_restriction: list[str] | None = None,
) -> list[schemas_memberships.UserMembershipComplete]:
    result = (
        (
            await db.execute(
                select(models_memberships.CoreAssociationUserMembership)
                .join(models_memberships.CoreAssociationMembership)
                .where(
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
                    models_memberships.CoreAssociationMembership.manager_group_id.in_(
                        manager_restriction,
                    )
                    if manager_restriction
                    else and_(True),
                ),
            )
        )
        .scalars()
        .all()
    )
    return [
        user_membership_complete_model_to_schema(membership) for membership in result
    ]


async def get_user_memberships_by_association_membership_id(
    db: AsyncSession,
    association_membership_id: UUID,
    minimal_start_date: date | None = None,
    maximal_start_date: date | None = None,
    minimal_end_date: date | None = None,
    maximal_end_date: date | None = None,
) -> list[schemas_memberships.UserMembershipComplete]:
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
        user_membership_complete_model_to_schema(membership) for membership in result
    ]


async def get_user_memberships_by_user_id_and_association_membership_id(
    db: AsyncSession,
    user_id: str,
    association_membership_id: UUID,
) -> list[schemas_memberships.UserMembershipComplete]:
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
        user_membership_complete_model_to_schema(membership) for membership in result
    ]


async def get_user_memberships_by_user_id_start_end_and_association_membership_id(
    db: AsyncSession,
    user_id: str,
    start_date: date,
    end_date: date,
    association_membership_id: UUID,
) -> list[schemas_memberships.UserMembershipComplete]:
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
        user_membership_complete_model_to_schema(membership) for membership in result
    ]


async def get_user_membership_by_id(
    db: AsyncSession,
    user_membership_id: UUID,
) -> schemas_memberships.UserMembershipWithAssociation | None:
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
    return user_membership_with_association_model_to_schema(result) if result else None


async def get_user_membership_by_document_id(
    db: AsyncSession,
    document_id: UUID,
) -> schemas_memberships.UserMembershipWithAssociation | None:
    result = (
        (
            await db.execute(
                select(models_memberships.CoreAssociationUserMembership).where(
                    models_memberships.CoreAssociationUserMembership.document_id
                    == document_id,
                ),
            )
        )
        .scalars()
        .first()
    )
    return user_membership_with_association_model_to_schema(result) if result else None


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
        document_id=user_membership.document_id,
        document_status=user_membership.document_status,
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
        .values(**user_membership_edit.model_dump(exclude_unset=True)),
    )


async def update_user_membership_document(
    db: AsyncSession,
    user_membership_id: UUID,
    document_id: UUID | None,
    document_status: DocumentStatus | None,
):
    await db.execute(
        update(models_memberships.CoreAssociationUserMembership)
        .where(
            models_memberships.CoreAssociationUserMembership.id == user_membership_id,
        )
        .values(document_id=document_id, document_status=document_status),
    )
