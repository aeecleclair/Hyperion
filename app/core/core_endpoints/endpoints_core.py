from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from app.core.core_endpoints import schemas_core
from app.core.utils.config import Settings
from app.dependencies import (
    get_settings,
)
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
    "/mypayment-terms-of-service",
    status_code=200,
)
async def read_mypayment_tos(settings: Settings = Depends(get_settings)):
    """
    Return MyPayment latest ToS
    """
    return patch_identity_in_text(
        Path("assets/mypayment-terms-of-service.txt").read_text(encoding="utf-8"),
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
        email_placeholder=settings.school.email_placeholder,
        main_activation_form=settings.school.main_activation_form,
        play_store_url=settings.school.play_store_url,
        app_store_url=settings.school.app_store_url,
        student_email_regex=settings.school.student_email_regex.pattern,
        staff_email_regex=settings.school.staff_email_regex.pattern
        if settings.school.staff_email_regex
        else None,
        former_student_email_regex=settings.school.former_student_email_regex.pattern
        if settings.school.former_student_email_regex
        else None,
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
