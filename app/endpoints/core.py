from os import path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.cruds import cruds_module_visibility
from app.dependencies import get_db, get_settings, is_user_a_member, is_user_a_member_of
from app.models import models_core
from app.schemas import schemas_core
from app.utils.tools import is_group_id_valid
from app.utils.types.groups_type import GroupType
from app.utils.types.module_list import ModuleList
from app.utils.types.tags import Tags

router = APIRouter()


@router.get(
    "/information",
    response_model=schemas_core.CoreInformation,
    status_code=200,
    tags=[Tags.core],
)
async def read_information(settings: Settings = Depends(get_settings)):
    """
    Return information about Hyperion. This endpoint can be used to check if the API is up.
    """

    return schemas_core.CoreInformation(
        ready=True,
        version=settings.HYPERION_VERSION,
        minimal_titan_version=settings.MINIMAL_TITAN_VERSION,
        minimal_titan_version_code=settings.MINIMAL_TITAN_VERSION_CODE,
    )


@router.get(
    "/privacy",
    response_class=FileResponse,
    status_code=200,
    tags=[Tags.core],
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
    tags=[Tags.core],
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
    tags=[Tags.core],
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
    tags=[Tags.core],
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
    tags=[Tags.core],
)
async def read_wellknown_security_txt():
    """
    Return Hyperion security.txt file
    """

    return FileResponse("assets/security.txt")


@router.get(
    "/style/{file}.css",
    response_class=FileResponse,
    status_code=200,
    tags=[Tags.core],
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
        (path.realpath(css_path), path.realpath(css_dir))
    ) != path.realpath(css_dir):
        raise HTTPException(status_code=404, detail="File not found")

    if not path.isfile(css_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(css_path)


@router.get(
    "/favicon.ico",
    response_class=FileResponse,
    status_code=200,
    tags=[Tags.core],
)
async def get_favicon():
    return FileResponse("assets/images/favicon.ico")


@router.get(
    "/module_visibility/",
    response_model=list[schemas_core.ModuleVisibility],
    status_code=200,
    tags=[Tags.core],
)
async def get_module_visibility(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Get all existing module_visibility.

    **This endpoint is only usable by administrators**
    """

    returnModuleVisibilities = []
    for module in ModuleList:
        allowed_group_ids = await cruds_module_visibility.get_allowed_groups_by_root(
            root=module.value.root, db=db
        )
        returnModuleVisibilities.append(
            schemas_core.ModuleVisibility(
                root=module.value.root,
                allowed_group_ids=allowed_group_ids,
            )
        )

    return returnModuleVisibilities


@router.get(
    "/module_visibility/me",
    response_model=list[str],
    status_code=200,
    tags=[Tags.core],
)
async def get_user_modules_visibility(
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member),
):
    """
    Get group user accessible root

    **This endpoint is only usable by everyone**
    """
    result = await cruds_module_visibility.get_modules_by_user(user=user, db=db)

    return result


@router.post(
    "/module_visibility/",
    response_model=schemas_core.ModuleVisibilityCreate,
    status_code=201,
    tags=[Tags.core],
)
async def add_module_visibility(
    module_visibility: schemas_core.ModuleVisibilityCreate,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    """
    Add a new group to a module

    **This endpoint is only usable by administrators**
    """

    # We need to check that loaner.group_manager_id is a valid group
    if not await is_group_id_valid(module_visibility.allowed_group_id, db=db):
        raise HTTPException(
            status_code=400,
            detail="Invalid id, group_id must be a valid group id",
        )
    try:
        module_visibility_db = models_core.ModuleVisibility(
            root=module_visibility.root,
            allowed_group_id=module_visibility.allowed_group_id,
        )

        return await cruds_module_visibility.create_module_visibility(
            module_visibility=module_visibility_db, db=db
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.delete(
    "/module_visibility/{root}/{group_id}", status_code=204, tags=[Tags.core]
)
async def delete_session(
    root: str,
    group_id: str,
    db: AsyncSession = Depends(get_db),
    user: models_core.CoreUser = Depends(is_user_a_member_of(GroupType.admin)),
):
    await cruds_module_visibility.delete_module_visibility(
        root=root, allowed_group_id=group_id, db=db
    )
