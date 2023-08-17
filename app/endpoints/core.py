from os import path

from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse

from app.api import Module
from app.core.config import Settings
from app.dependencies import get_settings
from app.schemas import schemas_core
from app.utils.types.tags import Tags

core = Module()


@core.router.get(
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


@core.router.get(
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


@core.router.get(
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


@core.router.get(
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


@core.router.get(
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


@core.router.get(
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


@core.router.get(
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


@core.router.get(
    "/favicon.ico",
    response_class=FileResponse,
    status_code=200,
    tags=[Tags.core],
)
async def get_favicon():
    return FileResponse("assets/images/favicon.ico")
