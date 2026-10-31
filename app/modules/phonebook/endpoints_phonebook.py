import logging
import uuid

from fastapi import Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups import cruds_groups, models_groups
from app.core.groups.groups_type import AccountType, GroupType
from app.core.permissions.cruds_permissions import get_permissions_by_permission_name
from app.core.permissions.type_permissions import ModulePermissions
from app.core.users import cruds_users, models_users
from app.dependencies import (
    get_db,
    is_user_allowed_to,
    is_user_in,
)
from app.modules.phonebook import cruds_phonebook, schemas_phonebook
from app.modules.phonebook.others.factory_phonebook import PhonebookFactory
from app.modules.phonebook.others.types_phonebook import RoleTags
from app.modules.phonebook.services import (
    association_service,
    groupment_service,
    membership_service,
)
from app.types import standard_responses
from app.types.content_type import ContentType
from app.types.module import Module
from app.utils.tools import (
    get_file_from_data,
    is_user_member_of_any_group,
    save_file_as_data,
)


class PhonebookPermissions(ModulePermissions):
    access_phonebook = "access_phonebook"
    manage_phonebook = "manage_phonebook"


module = Module(
    root="phonebook",
    tag="Phonebook",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=PhonebookFactory(),
    permissions=PhonebookPermissions,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


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


@module.router.get(
    "/phonebook/associations/",
    response_model=list[schemas_phonebook.AssociationComplete],
    status_code=200,
)
async def get_all_associations(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.access_phonebook]),
    ),
):
    """
    Return all associations from database as a list of AssociationComplete schemas
    """
    return await association_service.get_all_associations(db)


@module.router.get(
    "/phonebook/roletags",
    response_model=schemas_phonebook.RoleTagsReturn,
    status_code=200,
)
async def get_all_role_tags(
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.access_phonebook]),
    ),
):
    """
    Return all available role tags from RoleTags enum.
    """
    return membership_service.get_all_role_tags()


@module.router.get(
    "/phonebook/groupements/",
    response_model=list[schemas_phonebook.AssociationGroupement],
    status_code=200,
)
async def get_all_groupements(
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.access_phonebook]),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Return all groupements from database as a list of AssociationGroupement schemas
    """
    return await groupment_service.get_all_groupements(db)


@module.router.post(
    "/phonebook/groupements/",
    response_model=schemas_phonebook.AssociationGroupement,
    status_code=201,
)
async def create_groupement(
    groupement_base: schemas_phonebook.AssociationGroupementBase,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.manage_phonebook]),
    ),
    db: AsyncSession = Depends(get_db),
):
    return await groupment_service.create_groupement(groupement_base, db)


@module.router.patch(
    "/phonebook/groupements/{groupement_id}",
    status_code=204,
)
async def update_groupement(
    groupement_id: uuid.UUID,
    groupement_edit: schemas_phonebook.AssociationGroupementBase,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.manage_phonebook]),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a groupement
    """
    return await groupment_service.update_groupement(groupement_id, groupement_edit, db)


@module.router.delete(
    "/phonebook/groupements/{groupement_id}",
    status_code=204,
)
async def delete_groupement(
    groupement_id: uuid.UUID,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.manage_phonebook]),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a groupement
    """
    await groupment_service.delete_groupement(groupement_id, db)


@module.router.post(
    "/phonebook/associations/",
    response_model=schemas_phonebook.AssociationComplete,
    status_code=201,
)
async def create_association(
    association: schemas_phonebook.AssociationBase,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.access_phonebook]),
    ),
):
    """
    Create a new Association by giving an AssociationBase scheme
    """
    return await association_service.create_association(association, db, user)


@module.router.patch(
    "/phonebook/associations/{association_id}",
    status_code=204,
)
async def update_association(
    association_id: str,
    association_edit: schemas_phonebook.AssociationEdit,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.access_phonebook]),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an Association
    """
    await association_service.update_association(
        association_id,
        association_edit,
        user,
        db,
    )


@module.router.patch(
    "/phonebook/associations/{association_id}/groups",
    status_code=204,
)
async def update_association_groups(
    association_id: str,
    association_groups_edit: schemas_phonebook.AssociationGroupsEdit,
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the groups associated with an Association
    """
    await association_service.update_association_groups(
        association_id,
        association_groups_edit,
        db,
    )


@module.router.patch(
    "/phonebook/associations/{association_id}/deactivate",
    status_code=204,
)
async def deactivate_association(
    association_id: str,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.access_phonebook]),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate an Association
    """
    await association_service.deactivate_association(association_id, user, db)


@module.router.delete(
    "/phonebook/associations/{association_id}",
    status_code=204,
)
async def delete_association(
    association_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.access_phonebook]),
    ),
):
    """
    Delete an Association

    [!] Memberships linked to association_id will be deleted too
    """
    await association_service.delete_association(association_id, db, user)


@module.router.get(
    "/phonebook/associations/{association_id}/members/",
    response_model=list[schemas_phonebook.MemberComplete],
    status_code=200,
)
async def get_association_members(
    association_id: str,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.access_phonebook]),
    ),
    db: AsyncSession = Depends(get_db),
):
    """Return the list of MemberComplete of an Association."""
    return await membership_service.get_association_members(association_id, db)


@module.router.get(
    "/phonebook/associations/{association_id}/members/{mandate_year}",
    response_model=list[schemas_phonebook.MemberComplete],
    status_code=200,
)
async def get_association_members_by_mandate_year(
    association_id: str,
    mandate_year: int,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.access_phonebook]),
    ),
    db: AsyncSession = Depends(get_db),
):
    """Return the list of MemberComplete of an Association with given mandate_year."""
    return await membership_service.get_association_members_by_mandate_year(
        association_id,
        mandate_year,
        db,
    )


@module.router.get(
    "/phonebook/member/{user_id}",
    response_model=schemas_phonebook.MemberComplete,
    status_code=200,
)
async def get_member_details(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.access_phonebook]),
    ),
):
    """Return MemberComplete for given user_id."""
    return await membership_service.get_member_details(user_id, db)


@module.router.post(
    "/phonebook/associations/memberships",
    response_model=schemas_phonebook.MembershipComplete,
    status_code=201,
)
async def create_membership(
    membership: schemas_phonebook.MembershipBase,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.access_phonebook]),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new Membership.
    'role_tags' are used to indicate if the members has a main role in the association (president, secretary ...) and 'role_name' is the display name for this membership
    """
    return await membership_service.create_membership(membership, user, db)


@module.router.patch(
    "/phonebook/associations/memberships/{membership_id}",
    status_code=204,
)
async def update_membership(
    updated_membership: schemas_phonebook.MembershipEdit,
    membership_id: str,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.access_phonebook]),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a Membership.
    """
    await membership_service.update_membership(
        updated_membership,
        membership_id,
        user,
        db,
    )


@module.router.delete(
    "/phonebook/associations/memberships/{membership_id}",
    status_code=204,
)
async def delete_membership(
    membership_id: str,
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.access_phonebook]),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a membership.
    """
    await membership_service.delete_membership(membership_id, user, db)


@module.router.post(
    "/phonebook/associations/{association_id}/picture",
    response_model=standard_responses.Result,
    status_code=201,
)
async def create_association_logo(
    association_id: str,
    image: UploadFile = File(),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.access_phonebook]),
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a logo for an Association.
    **The user must be a member of the group CAA or BDE to use this endpoint**
    """
    await association_service.create_association_logo_validation(
        association_id,
        user,
        db,
    )

    await save_file_as_data(
        upload_file=image,
        directory="associations",
        filename=association_id,
        max_file_size=4 * 1024 * 1024,
        accepted_content_types=[
            ContentType.jpg,
            ContentType.png,
            ContentType.webp,
        ],
    )
    return standard_responses.Result(success=True)


@module.router.get(
    "/phonebook/associations/{association_id}/picture",
    response_class=FileResponse,
    status_code=200,
)
async def read_association_logo(
    association_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([PhonebookPermissions.access_phonebook]),
    ),
) -> FileResponse:
    """
    Get the logo of an Association.
    """
    await association_service.read_association_logo_validation(
        association_id,
        db,
    )
    return await get_file_from_data(
        directory="associations",
        filename=association_id,
        default_asset="assets/images/default_association_picture.png",
    )
