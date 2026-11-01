import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions.cruds_permissions import get_permissions_by_permission_name
from app.core.users import models_users
from app.modules.phonebook import cruds_phonebook, schemas_phonebook
from app.modules.phonebook.endpoints_phonebook import PhonebookPermissions
from app.modules.phonebook.others import exceptions_phonebook
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


async def validate_rights(
    db: AsyncSession,
    user: models_users.CoreUser,
    groupement_id: uuid.UUID,
    detail: str,
) -> None:
    if not await has_association_groupement_manager_rights(
        db=db,
        user=user,
        groupement_id=groupement_id,
    ):
        raise exceptions_phonebook.ForbiddenException(detail)


async def validate_rights_or_is_president(
    association_id: str,
    mandate_year: int,
    groupement_id: uuid.UUID,
    user: models_users.CoreUser,
    db: AsyncSession,
    detail: str,
) -> None:
    if not await has_association_groupement_manager_rights(
        db=db,
        user=user,
        groupement_id=groupement_id,
    ) and not await cruds_phonebook.is_user_president(
        association_id=association_id,
        mandate_year=mandate_year,
        user=user,
        db=db,
    ):
        raise exceptions_phonebook.ForbiddenException(detail)


async def association_if_exists(
    association_id: str,
    db: AsyncSession,
) -> schemas_phonebook.AssociationComplete:
    association = await cruds_phonebook.get_association_by_id(association_id, db)
    if association is None:
        raise exceptions_phonebook.NotFoundException(  # noqa: TRY003
            "Association not found.",
        )
    return association
