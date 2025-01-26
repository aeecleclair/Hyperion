import logging
from os import path
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.core_endpoints import cruds_core, models_core, schemas_core
from app.core.groups.groups_type import AccountType, GroupType
from app.dependencies import (
    get_db,
    get_settings,
    is_user,
    is_user_in,
)
from app.modules.module_list import module_list
from app.types.module import CoreModule
from app.utils.tools import is_group_id_valid

router = APIRouter(tags=["Core"])

core_module = CoreModule(
    root="",
    tag="Core",
    router=router,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


@router.get(
    "/information",
    response_model=schemas_core.CoreInformation,
    status_code=200,
)
async def read_information(
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
    response_class=FileResponse,
    status_code=200,
)
async def read_privacy():
    """
    Return Hyperion privacy
    """

    return FileResponse("assets/privacy.txt")


@router.get(
    "/terms-and-conditions",
    response_class=FileResponse,
    status_code=200,
)
async def read_terms_and_conditions():
    """
    Return Hyperion terms and conditions pages
    """

    return FileResponse("assets/terms-and-conditions.txt")


@router.get(
    "/support",
    response_class=FileResponse,
    status_code=200,
)
async def read_support():
    """
    Return Hyperion terms and conditions pages
    """

    return FileResponse("assets/support.txt")


@router.get(
    "/security.txt",
    response_class=FileResponse,
    status_code=200,
)
async def read_security_txt():
    """
    Return Hyperion security.txt file
    """

    return FileResponse("assets/security.txt")


@router.get(
    "/.well-known/security.txt",
    response_class=FileResponse,
    status_code=200,
)
async def read_wellknown_security_txt():
    """
    Return Hyperion security.txt file
    """

    return FileResponse("assets/security.txt")


@router.get(
    "/robots.txt",
    response_class=FileResponse,
    status_code=200,
)
async def read_robots_txt():
    """
    Return Hyperion robots.txt file
    """

    return FileResponse("assets/robots.txt")


@router.get(
    "/style/{file}.css",
    response_class=FileResponse,
    status_code=200,
)
async def get_style_file(
    file: str,
):
    """
    Return a style file from the assets folder
    """
    css_dir = "assets/style/"
    css_path = f"{css_dir}{file}.css"

    # Security check (even if FastAPI parsing of path parameters does not allow path traversal)
    if path.commonprefix(
        (path.realpath(css_path), path.realpath(css_dir)),
    ) != path.realpath(css_dir):
        raise HTTPException(status_code=404, detail="File not found")

    if not Path(css_path).is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(css_path)


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
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
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
    user: models_core.CoreUser = Depends(is_user()),
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
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
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
        try:
            return await cruds_core.create_module_group_visibility(
                module_visibility=module_group_visibility_db,
                db=db,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))

    if module_visibility.allowed_account_type is not None:
        module_account_visibility_db = models_core.ModuleAccountTypeVisibility(
            root=module_visibility.root,
            allowed_account_type=module_visibility.allowed_account_type,
        )
        try:
            return await cruds_core.create_module_account_type_visibility(
                module_visibility=module_account_visibility_db,
                db=db,
            )
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error))


@router.delete("/module-visibility/{root}/groups/{group_id}", status_code=204)
async def delete_module_group_visibility(
    root: str,
    group_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
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
    user: models_core.CoreUser = Depends(is_user_in(GroupType.admin)),
):
    await cruds_core.delete_module_account_type_visibility(
        root=root,
        allowed_account_type=account_type,
        db=db,
    )
