from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.core_endpoints import cruds_core, models_core, schemas_core
from app.core.groups.groups_type import AccountType, GroupType
from app.core.users import models_users
from app.core.utils.config import Settings
from app.dependencies import (
    get_db,
    get_settings,
    is_user,
    is_user_in,
)
from app.module import module_list
from app.types.module import CoreModule
from app.utils.tools import is_group_id_valid, patch_identity_in_text

router = APIRouter(tags=["Core"])

core_module = CoreModule(
    root="core",
    tag="Core",
    router=router,
    factory=None,
)


@router.get(
    "/information",
    response_model=schemas_core.CoreInformation,
    status_code=200,
)
async def read_information(
    request: Request,
    settings: Settings = Depends(get_settings),
):
    """
    Return information about Hyperion. This endpoint can be used to check if the API is up.
    """

    return schemas_core.CoreInformation(
        ready=True,
        version=settings.HYPERION_VERSION,
        minimal_titan_version_code=settings.MINIMAL_TITAN_VERSION_CODE,
    )


@router.get(
    "/privacy",
    status_code=200,
)
async def read_privacy(settings: Settings = Depends(get_settings)):
    """
    Return Hyperion privacy
    """

    return patch_identity_in_text(
        Path("assets/privacy.txt").read_text(encoding="utf-8"),
        settings,
    )


@router.get(
    "/terms-and-conditions",
    status_code=200,
)
async def read_terms_and_conditions(settings: Settings = Depends(get_settings)):
    """
    Return Hyperion terms and conditions pages
    """

    return patch_identity_in_text(
        Path("assets/terms-and-conditions.txt").read_text(encoding="utf-8"),
        settings,
    )


@router.get(
    "/myeclpay-terms-of-service",
    status_code=200,
)
async def read_myeclpay_tos(settings: Settings = Depends(get_settings)):
    """
    Return MyECLPay latest ToS
    """
    return patch_identity_in_text(
        Path("assets/myeclpay-terms-of-service.txt").read_text(encoding="utf-8"),
        settings,
    )


@router.get(
    "/support",
    status_code=200,
)
async def read_support(settings: Settings = Depends(get_settings)):
    """
    Return Hyperion support
    """

    return patch_identity_in_text(
        Path("assets/support.txt").read_text(encoding="utf-8"),
        settings,
    )


@router.get(
    "/security.txt",
    status_code=200,
)
async def read_security_txt(settings: Settings = Depends(get_settings)):
    """
    Return Hyperion security.txt file
    """
    return patch_identity_in_text(
        Path("assets/security.txt").read_text(encoding="utf-8"),
        settings,
    )


@router.get(
    "/.well-known/security.txt",
    status_code=200,
)
async def read_wellknown_security_txt(settings: Settings = Depends(get_settings)):
    """
    Return Hyperion security.txt file
    """

    return patch_identity_in_text(
        Path("assets/security.txt").read_text(encoding="utf-8"),
        settings,
    )


@router.get(
    "/robots.txt",
    status_code=200,
)
async def read_robots_txt(settings: Settings = Depends(get_settings)):
    """
    Return Hyperion robots.txt file
    """

    return patch_identity_in_text(
        Path("assets/robots.txt").read_text(encoding="utf-8"),
        settings,
    )


@router.get(
    "/variables",
    response_model=schemas_core.CoreVariables,
    status_code=200,
)
async def get_variables(settings: Settings = Depends(get_settings)):
    """
    Return a style file from the assets folder
    """
    return schemas_core.CoreVariables(
        name=settings.school.application_name,
        entity_name=settings.school.entity_name,
        # `as_hsl()` return a string in the format `hsl(hue saturation lightness)`, we need to convert it to `24.6 95% 53.1%` for TailwindCSS
        primary_color=settings.school.primary_color.as_hsl()[4:-1],
    )


@router.get(
    "/favicon.ico",
    response_class=FileResponse,
    status_code=200,
)
async def get_favicon():
    return FileResponse("assets/images/favicon.ico")


@router.get(
    "/module-visibility/",
    response_model=list[schemas_core.ModuleVisibility],
    status_code=200,
)
async def get_module_visibility(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Get all existing module_visibility.

    **This endpoint is only usable by administrators**
    """

    return_module_visibilities = []
    for module in module_list:
        allowed_group_ids = await cruds_core.get_allowed_groups_by_root(
            root=module.root,
            db=db,
        )
        allowed_account_types = await cruds_core.get_allowed_account_types_by_root(
            root=module.root,
            db=db,
        )
        return_module_visibilities.append(
            schemas_core.ModuleVisibility(
                root=module.root,
                allowed_group_ids=allowed_group_ids,
                allowed_account_types=allowed_account_types,
            ),
        )

    return return_module_visibilities


@router.get(
    "/module-visibility/me",
    response_model=list[str],
    status_code=200,
)
async def get_user_modules_visibility(
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user()),
):
    """
    Get group user accessible root

    **This endpoint is only usable by everyone**
    """

    return await cruds_core.get_modules_by_user(user=user, db=db)


@router.post(
    "/module-visibility/",
    status_code=201,
)
async def add_module_visibility(
    module_visibility: schemas_core.ModuleVisibilityCreate,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    """
    Add a new group or account type to a module

    **This endpoint is only usable by administrators**
    """
    if (
        module_visibility.allowed_group_id is None
        and module_visibility.allowed_account_type is None
    ):
        raise HTTPException(
            status_code=400,
            detail="allowed_group_id or allowed_account_type must be set",
        )

    if module_visibility.allowed_group_id is not None:
        # We need to check that loaner.group_manager_id is a valid group
        if not await is_group_id_valid(module_visibility.allowed_group_id, db=db):
            raise HTTPException(
                status_code=400,
                detail="Invalid id, group_id must be a valid group id",
            )
        module_group_visibility_db = models_core.ModuleGroupVisibility(
            root=module_visibility.root,
            allowed_group_id=module_visibility.allowed_group_id,
        )

        await cruds_core.create_module_group_visibility(
            module_visibility=module_group_visibility_db,
            db=db,
        )

    if module_visibility.allowed_account_type is not None:
        module_account_visibility_db = models_core.ModuleAccountTypeVisibility(
            root=module_visibility.root,
            allowed_account_type=module_visibility.allowed_account_type,
        )

        await cruds_core.create_module_account_type_visibility(
            module_visibility=module_account_visibility_db,
            db=db,
        )


@router.delete("/module-visibility/{root}/groups/{group_id}", status_code=204)
async def delete_module_group_visibility(
    root: str,
    group_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    await cruds_core.delete_module_group_visibility(
        root=root,
        allowed_group_id=group_id,
        db=db,
    )


@router.delete(
    "/module-visibility/{root}/account-types/{account_type}",
    status_code=204,
)
async def delete_module_account_type_visibility(
    root: str,
    account_type: AccountType,
    db: AsyncSession = Depends(get_db),
    user: models_users.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    await cruds_core.delete_module_account_type_visibility(
        root=root,
        allowed_account_type=account_type,
        db=db,
    )
