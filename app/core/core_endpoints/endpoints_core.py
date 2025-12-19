from os import path
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from app.core.core_endpoints import schemas_core
from app.core.utils.config import Settings
from app.dependencies import (
    get_settings,
)
from app.types.module import CoreModule

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
    "/myeclpay-terms-of-service",
    response_class=FileResponse,
    status_code=200,
)
async def read_myeclpay_tos():
    """
    Return MyECLPay latest ToS
    """
    return FileResponse("assets/myeclpay-terms-of-service.txt")


@router.get(
    "/support",
    response_class=FileResponse,
    status_code=200,
)
async def read_support():
    """
    Return Hyperion support
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
