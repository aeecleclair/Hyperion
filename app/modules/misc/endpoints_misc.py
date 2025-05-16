import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType, GroupType
from app.core.users import models_users
from app.dependencies import get_db, is_user_a_member, is_user_in
from app.modules.misc import core_data_misc, schemas_misc
from app.types.module import Module
from app.utils import tools

router = APIRouter()


# <-- Contacts for PE5 SafetyCards 2025 -->
module = Module(
    root="contacts_safety_cards",
    tag="Contact",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
)


@module.router.get(
    "/contacts_safety_cards/contacts",
    response_model=list[schemas_misc.ContactBase],
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

    contacts_from_core_data = await tools.get_core_data(
        core_data_misc.ContactSafetyCards,
        db,
    )

    serialized_json_contacts = contacts_from_core_data.contacts

    return json.loads(serialized_json_contacts)


@module.router.put(
    "/contacts_safety_cards/contacts",
    status_code=201,
)
async def set_contacts(
    contacts: list[schemas_misc.ContactBase],
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.eclair)),
):
    """
    Create a contact.

    **This endpoint is only usable by members of the group eclair**
    """

    contacts_serialized_json = json.dumps(contacts)

    await tools.set_core_data(
        core_data_misc.ContactSafetyCards(contacts=contacts_serialized_json),
        db,
    )
# <-- End of Contacts for PE5 SafetyCards 2025 -->
