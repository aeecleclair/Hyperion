import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.misc import models_misc, schemas_misc


# <-- Contacts for PE5 SafetyCards -->
async def get_contacts(
    db: AsyncSession,
) -> Sequence[models_misc.Contacts]:
    result = await db.execute(select(models_misc.Contacts))
    return result.scalars().all()


async def create_contact(
    contact: models_misc.Contacts,
    db: AsyncSession,
) -> models_misc.Contacts:
    db.add(contact)
    await db.commit()
    return contact


async def update_contact(
    contact_id: uuid.UUID,
    contact: schemas_misc.ContactEdit,
    db: AsyncSession,
):
    if not bool(contact.model_fields_set):
        return

    result = await db.execute(
        update(models_misc.Contacts)
        .where(models_misc.Contacts.id == contact_id)
        .values(**contact.model_dump(exclude_none=True)),
    )
    if result.rowcount == 1:
        await db.commit()
    else:
        await db.rollback()
        raise ValueError


async def delete_contact(
    contact_id: uuid.UUID,
    db: AsyncSession,
):
    result = await db.execute(
        delete(models_misc.Contacts).where(
            models_misc.Contacts.id == contact_id,
        ),
    )
    if result.rowcount == 1:
        await db.commit()
    else:
        await db.rollback()
        raise ValueError


async def get_contact_by_id(
    contact_id: uuid.UUID,
    db: AsyncSession,
) -> models_misc.Contacts | None:
    result = await db.execute(
        select(models_misc.Contacts).where(
            models_misc.Contacts.id == contact_id,
        ),
    )
    return result.scalars().one_or_none()


# <-- End of Contacts for PE5 SafetyCards -->
