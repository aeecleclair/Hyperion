from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import (
    Depends,
    HTTPException,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.groups.groups_type import AccountType
from app.core.permissions.type_permissions import ModulePermissions
from app.core.users import models_users
from app.core.utils.security import generate_token
from app.dependencies import (
    get_db,
    is_user,
    is_user_allowed_to,
)
from app.modules.identity import cruds_identity, schemas_identity
from app.types.module import Module
from app.utils.tools import (
    is_user_member_of_any_group,
)


class IdentityPermissions(ModulePermissions):
    manage_identity = "manage_identity"
    access_identity = "access_identity"


module = Module(
    root="identity",
    tag="Identity",
    default_allowed_account_types=[AccountType.student, AccountType.staff],
    factory=None,
    permissions=IdentityPermissions,
)


@module.router.post(
    "/identity/verification-contexts",
    response_model=schemas_identity.VerificationContext,
    status_code=201,
)
async def create_verification_context(
    context_creation: schemas_identity.VerificationContextCreation,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([IdentityPermissions.manage_identity]),
    ),
):
    """
    Create a new verification context for a group.

    **Only users with the `manage_identity` permission can perform this action for context of groups they are a member of**
    """
    if not is_user_member_of_any_group(user, [context_creation.group_id]):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized to create context for this group",
        )
    context = schemas_identity.VerificationContext(
        id=uuid4(),
        name=context_creation.name,
        archived=False,
        group_id=context_creation.group_id,
    )
    await cruds_identity.create_verification_context(
        db=db,
        verification_context=context,
    )
    return context


@module.router.get(
    "/identity/verification-contexts",
    response_model=list[schemas_identity.VerificationContextComplete],
    status_code=200,
)
async def get_user_verification_contexts(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([IdentityPermissions.access_identity]),
    ),
):
    """
    Return all verification contexts for the groups the user is a member of.
    """

    return await cruds_identity.get_verification_contexts_by_group_ids(
        group_ids=[group.id for group in user.groups],
        db=db,
    )


@module.router.patch(
    "/identity/verification-contexts/{context_id}",
    status_code=204,
)
async def edit_verification_context(
    context_id: UUID,
    context_edit: schemas_identity.VerificationContextEdit,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([IdentityPermissions.manage_identity]),
    ),
):
    """
    Mark a verification context as archived or non archived.

    **Only users with the `manage_identity` permission can perform this action for context of groups they are a member of**
    """
    context = await cruds_identity.get_verification_context_by_id(
        context_id=context_id,
        db=db,
    )
    if context is None:
        raise HTTPException(
            status_code=404,
            detail="Verification context not found",
        )

    if not is_user_member_of_any_group(user, [context.group_id]):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized to modify this context",
        )

    await cruds_identity.update_verification_context_edit(
        context_id=context_id,
        context_edit=context_edit,
        db=db,
    )


@module.router.get(
    "/identity/verification-contexts/{context_id}/scans",
    response_model=list[schemas_identity.VerificationScan],
    status_code=200,
)
async def get_scans(
    context_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([IdentityPermissions.access_identity]),
    ),
):
    """
    Get all verification scans for a verification context.

    **Only users with the `access_identity` permission can perform this action for context of groups they are a member of**
    """
    context = await cruds_identity.get_verification_context_by_id(
        context_id=context_id,
        db=db,
    )
    if context is None:
        raise HTTPException(
            status_code=404,
            detail="Verification context not found",
        )

    if not is_user_member_of_any_group(user, [context.group_id]):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized to ask information for this context",
        )

    return await cruds_identity.get_verification_scans_by_context_id(
        context_id=context_id,
        db=db,
    )


@module.router.get(
    "/identity/verification-contexts/{context_id}/scans/{token}/info",
    response_model=schemas_identity.IdentityTokenResponse,
    status_code=200,
)
async def ask_for_identity_token_information(
    context_id: UUID,
    token: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([IdentityPermissions.access_identity]),
    ),
):
    """
    Ask information about the identity of a user.

    **Only users with the `access_identity` permission can perform this action for context of groups they are a member of**
    """
    context = await cruds_identity.get_verification_context_by_id(
        context_id=context_id,
        db=db,
    )
    if context is None:
        raise HTTPException(
            status_code=404,
            detail="Verification context not found",
        )

    if not is_user_member_of_any_group(user, [context.group_id]):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized to ask information for this context",
        )

    identity_token = await cruds_identity.get_identity_information_by_token(
        token=token,
        db=db,
    )

    if identity_token is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid token",
        )

    if identity_token.expire_on < datetime.now(UTC):
        raise HTTPException(
            status_code=400,
            detail="Identity token has expired",
        )

    other_scans = await cruds_identity.get_verification_scans_by_context_id_and_user_id(
        context_id=context_id,
        user_id=identity_token.user_id,
        db=db,
    )

    return schemas_identity.IdentityTokenResponseComplete(
        id=identity_token.id,
        token=identity_token.token,
        user_id=identity_token.user_id,
        expire_on=identity_token.expire_on,
        firstname=identity_token.firstname,
        name=identity_token.name,
        nickname=identity_token.nickname,
        already_scanned=len(other_scans) > 0,
    )


@module.router.post(
    "/identity/verification-contexts/{context_id}/scans/{token}/scan",
    status_code=204,
)
async def scan_identity_token(
    context_id: UUID,
    token: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user_allowed_to([IdentityPermissions.access_identity]),
    ),
):
    """
    Mark an identity token as scanned for a verification context.

    **Only users with the `access_identity` permission can perform this action for context of groups they are a member of**
    """
    context = await cruds_identity.get_verification_context_by_id(
        context_id=context_id,
        db=db,
    )
    if context is None:
        raise HTTPException(
            status_code=404,
            detail="Verification context not found",
        )

    if not is_user_member_of_any_group(user, [context.group_id]):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized to ask information for this context",
        )

    identity_token = await cruds_identity.get_identity_information_by_token(
        token=token,
        db=db,
    )

    if identity_token is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid token",
        )

    if identity_token.expire_on < datetime.now(UTC):
        raise HTTPException(
            status_code=400,
            detail="Identity token has expired",
        )

    await cruds_identity.create_verification_scan(
        scan=schemas_identity.VerificationScan(
            id=uuid4(),
            user_id=identity_token.user_id,
            verification_context_id=context_id,
            datetime=datetime.now(UTC),
            scanner_user_id=user.id,
        ),
        db=db,
    )


@module.router.post(
    "/identity/users/me/create-token",
    response_model=schemas_identity.IdentityToken,
    status_code=200,
)
async def ask_for_identity_token(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(
        is_user(),
    ),
):
    identity_token = schemas_identity.IdentityToken(
        id=uuid4(),
        token=generate_token(),
        user_id=user.id,
        expire_on=datetime.now(UTC) + timedelta(minutes=2),
    )

    await cruds_identity.create_identity_token(
        identity_token=identity_token,
        db=db,
    )

    return identity_token
