from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from app.core.config import Settings
from app.dependencies import get_settings
from app.utils.mail.mailworker import send_email

router = APIRouter()


@router.post("/send-email/")
def send_email_backgroundtasks(
    email: str,
    subject: str,
    content: str,
    settings: Settings = Depends(get_settings),
):
    # TODO: WARNING this endpoint should be removed or restricted

    send_email(email, subject, content, settings=settings)
    return JSONResponse(status_code=200, content={"message": "email has been sent"})
