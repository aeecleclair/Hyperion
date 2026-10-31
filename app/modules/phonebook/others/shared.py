import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions.cruds_permissions import get_permissions_by_permission_name
from app.core.users import models_users
from app.modules.phonebook import cruds_phonebook
from app.modules.phonebook.endpoints_phonebook import PhonebookPermissions
from app.utils.tools import is_user_member_of_any_group


async def has_association_groupement_manager_rights(
    db: AsyncSession,
    user: models_users.CoreUser,
    groupement_id: uuid.UUID,
) -> bool:
    """Check if the user has manager rights for the association groupement."""
    groupement = await cruds_phonebook.get_groupement_by_id(
        db=db,
        groupement_id=groupement_id,
    )
    if not groupement:
        return False

    permissions = await get_permissions_by_permission_name(
        db=db,
        permission_name=PhonebookPermissions.manage_phonebook,
    )

    return is_user_member_of_any_group(
        user=user,
        allowed_groups=[groupement.manager_group_id, *permissions.groups],
    )
