import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType, GroupType
from app.core.users import models_users
from app.dependencies import get_db, is_user_a_member, is_user_in
from app.modules.misc import cruds_misc, models_misc, schemas_misc
from app.types.module import Module

router = APIRouter()


# <-- Contacts for PE5 -->
module = Module(
    root="contact",
    tag="Contact",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
)


@module.router.get(
    "/contact/contacts",
    response_model=list[schemas_misc.Contact],
    status_code=200,
)
async def get_contacts(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_a_member),
):
    """
    Get contacts.

    **The user must be authenticated to use this endpoint**
    This the main purpose of this endpoint, because contacts (phone numbers, emails) should not be leaked in the prevention website
    """

    return await cruds_misc.get_contacts(db=db)


@module.router.post(
    "/contact/contacts",
    response_model=schemas_misc.Contact,
    status_code=201,
)
async def create_contact(
    contact: schemas_misc.ContactBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.eclair)),
):
    """
    Create a contact.

    **This endpoint is only usable by members of the group eclair**
    """

    contact_db = models_misc.Contacts(
        id=uuid.uuid4(),
        creation=datetime.now(UTC),
        **contact.model_dump(),
    )

    return await cruds_misc.create_contact(
        contact=contact_db,
        db=db,
    )


@module.router.patch(
    "/contact/contacts/{contact_id}",
    status_code=204,
)
async def edit_contact(
    contact_id: uuid.UUID,
    contact: schemas_misc.ContactEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.eclair)),
):
    """
    Edit a contact.

    **This endpoint is only usable by members of the group eclair**
    """

    try:
        await cruds_misc.update_contact(
            contact_id=contact_id,
            contact=contact,
            db=db,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="The contact does not exist")


@module.router.delete(
    "/contact/contacts/{contact_id}",
    status_code=204,
)
async def delete_contact(
    contact_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.eclair)),
):
    """
    Delete a contact.

    **This endpoint is only usable by members of the group eclair**
    """

    try:
        await cruds_misc.delete_contact(
            db=db,
            contact_id=contact_id,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="The contact does not exist")


# <-- End of Contacts for PE5 -->
