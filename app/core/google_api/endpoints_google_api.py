import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.google_api.google_api import GoogleAPI
from app.dependencies import (
    get_db,
    get_settings,
)
from app.types.module import CoreModule

router = APIRouter(tags=["GoogleAPI"])

core_module = CoreModule(
    root="google-api",
    tag="GoogleAPI",
    router=router,
)

hyperion_error_logger = logging.getLogger("hyperion.error")


@router.get("/google-api/oauth2callback", status_code=200)
async def google_api_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    try:
        await GoogleAPI().authentication_callback(
            db=db,
            settings=settings,
            request=request,
        )

    except Exception:
        hyperion_error_logger.exception(
            "Google API authentication callback error",
        )
        return "An error occurred during the Google API authentication callback"

    return "Ok"
