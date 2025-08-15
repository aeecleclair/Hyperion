import uuid
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.associations import models_associations, schemas_associations


async def get_associations(
    db: AsyncSession,
) -> Sequence[models_associations.CoreAssociation]:
    result = await db.execute(select(models_associations.CoreAssociation))
    return result.scalars().all()


async def get_associations_for_groups(
    group_ids: list[str],
    db: AsyncSession,
) -> Sequence[models_associations.CoreAssociation]:
    result = await db.execute(
        select(models_associations.CoreAssociation).where(
            models_associations.CoreAssociation.group_id.in_(group_ids),
        ),
    )
    return result.scalars().all()


async def get_association_by_id(
    association_id: uuid.UUID,
    db: AsyncSession,
) -> models_associations.CoreAssociation | None:
    result = await db.execute(
        select(models_associations.CoreAssociation).where(
            models_associations.CoreAssociation.id == association_id,
        ),
    )
    return result.scalars().first()


async def get_association_by_name(
    name: str,
    db: AsyncSession,
) -> models_associations.CoreAssociation | None:
    result = await db.execute(
        select(models_associations.CoreAssociation).where(
            models_associations.CoreAssociation.name == name,
        ),
    )
    return result.scalars().first()


async def create_association(
    db: AsyncSession,
    association: models_associations.CoreAssociation,
) -> None:
    db.add(association)


async def update_association(
    db: AsyncSession,
    association_id: UUID,
    association_update: schemas_associations.AssociationUpdate,
) -> None:
    await db.execute(
        update(models_associations.CoreAssociation)
        .where(models_associations.CoreAssociation.id == association_id)
        .values(**association_update.model_dump(exclude_unset=True)),
    )
